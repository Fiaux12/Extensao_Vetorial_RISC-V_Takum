"""
experimento.py
Fase 3: y = A . x no Takum (executado no simulador) e no padrão IEEE
(FP8/FP16/FP32, aproximado em Python), com o erro relativo de cada um
medido contra uma referência em precisão alta.

Executar:  python experimento.py
"""
import random
from decimal import Decimal, localcontext
from estruturas import Maquina, VLEN
from codificacao import montar
from takum import float_para_takum, takum_para_float
from main import executar

# --- Parâmetros do experimento ----------------------------------------------
LINHAS = 16
COLUNAS = 32
ESPARSIDADE = 0.7           # fração de zeros em A
SEMENTE = 42
LARGURAS = (8, 16, 32)      # T8/T16/T32 e FP8/FP16/FP32

# --- Endereços na memória do simulador (bytes) --------------------------------
END_A = 0x0000              # linha atual de A
END_X = 0x2000              # vetor x
END_ACC = 0x3000            # acumulador inicial (zero)
END_Y = 0x3100              # resultado da linha


# =============================================================================
# 1. Dados e referência
# =============================================================================
def gerar_dados(linhas: int, colunas: int, esparsidade: float, semente: int):
    """Devolve (A, x): A como lista de listas de float, com a fração
    `esparsidade` de zeros; x como lista de float. Usa random com semente fixa."""
    rng = random.Random(semente)               # gerador próprio: não mexe no random global
 
    def valor():
        return rng.uniform(-1.0, 1.0)
 
    A = [[0.0 if rng.random() < esparsidade else valor() for _ in range(colunas)]
         for _ in range(linhas)]
    x = [valor() for _ in range(colunas)]
    return A, x
 
 
def calcular_referencia(A: list, x: list) -> list:
    """y_ref = A . x em precisão alta (decimal com 34 dígitos, como o Float128),
    a partir dos valores originais. Devolve uma lista de Decimal."""
    with localcontext() as ctx:
        ctx.prec = 34
        x_dec = [Decimal(v) for v in x]        # Decimal(float) é exato
        y_ref = []
        for linha in A:
            soma = Decimal(0)
            for a, xj in zip(linha, x_dec):
                soma += Decimal(a) * xj
            y_ref.append(soma)
    return y_ref


# =============================================================================
# 2. Lado Takum (executado no simulador)
# =============================================================================
def pedaco_elementos(n: int) -> int:
    if n not in (8, 16, 32):
        raise ValueError(f"largura inválida: {n}")
    lanes = VLEN // 32                  # o vtdot exige SEW = 32, então vl máximo = VLEN/32
    return lanes * (32 // n)


def escrever_vetor_na_memoria(m: Maquina, endereco: int, valores: list, n: int,
                              tamanho_total: int) -> None:
    """Converte cada valor para Takum de n bits e grava na memória (little-endian),
    completando com zeros até `tamanho_total` elementos."""

    if len(valores) > tamanho_total:
        raise ValueError(f"{len(valores)} valores não cabem em {tamanho_total} elementos")
    n_bytes = n // 8
    dados = bytearray()
    for v in valores:
        dados += float_para_takum(v, n).to_bytes(n_bytes, "little")
    dados += bytes((tamanho_total - len(valores)) * n_bytes)    # zero em Takum = bits 0
    m.escrever_memoria(endereco, bytes(dados))


def montar_programa_linha(n: int, n_pedacos: int) -> list:
    """Programa de uma linha: para cada pedaço, vle32.v (A), vle32.v (x),
    vtdotN.vv acumulando em v3[0]; ao final, vse32.v do escalar.
    Os endereços ficam nos registradores a0..a3 (definidos pelo Python):
        a0 = linha de A | a1 = x | a2 = acumulador inicial (zero) | a3 = destino de y"""
    if n not in (8, 16, 32):
        raise ValueError(f"largura inválida: {n}")
    if n_pedacos < 1:
        raise ValueError("a linha precisa de pelo menos 1 pedaço")

    lanes = VLEN // 32                    # vl do vtdot (SEW = 32)
    bytes_pedaco = VLEN // 8              # cada vle32.v com vl = lanes traz 16 bytes

    linhas = [
        f"li t1, {lanes}",
        "vsetvli t0, t1, e32, m1, ta, ma",
        "vle32.v v3, (a2)",               # acumulador inicial (zero) em v3[0]
    ]
    for _ in range(n_pedacos):
        linhas += [
            "vle32.v v1, (a0)",           # pedaço da linha de A
            "vle32.v v2, (a1)",           # pedaço de x
            f"vtdot{n}.vv v3, v2, v1",    # v3[0] += soma dos produtos do pedaço
            f"addi a0, a0, {bytes_pedaco}",
            f"addi a1, a1, {bytes_pedaco}",
        ]
    linhas += [
        "li t1, 1",
        "vsetvli t0, t1, e32, m1, ta, ma",  # vl = 1: grava só o escalar
        "vse32.v v3, (a3)",
    ]
    return montar(linhas)


def executar_takum_linha(m: Maquina, linha: list, x: list, n: int) -> float:
    """Roda uma linha de A no simulador e devolve y[i] (float, decodificado)."""
    ped = pedaco_elementos(n)
    n_pedacos = -(-len(linha) // ped)                 # divisão para cima
    total = n_pedacos * ped                           # elementos gravados (com zeros)
    if total * (n // 8) > END_ACC - END_X:
        raise ValueError("a linha não cabe na região de memória reservada")

    # 1. dados na memória
    escrever_vetor_na_memoria(m, END_A, linha, n, total)
    escrever_vetor_na_memoria(m, END_X, x, n, total)

    # 2. endereços nos registradores a0..a3 (x10..x13)
    for reg, endereco in ((10, END_A), (11, END_X), (12, END_ACC), (13, END_Y)):
        m.escrever_escalar(reg, endereco)

    # 3. programa e execução
    m.carregar_programa(montar_programa_linha(n, n_pedacos))
    executar(m)

    # 4. resultado: um T32 em END_Y
    bits = int.from_bytes(m.ler_memoria(END_Y, 4), "little")
    return takum_para_float(bits, 32)

def executar_takum(A: list, x: list, n: int) -> list:
    """y = A . x em T<n>: uma linha por vez, com Maquina nova a cada linha."""
    return [executar_takum_linha(Maquina(), linha, x, n) for linha in A]


# =============================================================================
# 3. Lado padrão IEEE (aproximado em Python)
# =============================================================================
def quantizar_ieee(valor: float, n: int) -> float:
    """Arredonda para FP<n> e devolve como float. FP16/FP32: numpy.
    FP8: conversão de ida e volta (PyTorch ou ml_dtypes)."""
    raise NotImplementedError


def calcular_padrao(A: list, x: list, n: int) -> list:
    """y = A . x com A e x guardados em FP<n> (quantizar_ieee) e a
    multiplicação feita pelos operadores normais do Python."""
    raise NotImplementedError


# =============================================================================
# 4. Erro e relatório
# =============================================================================
def erro_relativo(y: list, y_ref: list):
    """Devolve (erros, n_excluidos): |y - y_ref| / |y_ref| por linha,
    excluindo (e contando) as linhas com y_ref == 0."""
    raise NotImplementedError


def resumir(erros: list) -> dict:
    """Mediana, percentil 95 e máximo dos erros."""
    raise NotImplementedError


def imprimir_tabela(resultados: dict) -> None:
    """Tabela com uma linha por formato (T8, T16, T32, FP8, FP16, FP32)."""
    raise NotImplementedError


def main() -> None:
    A, x = gerar_dados(LINHAS, COLUNAS, ESPARSIDADE, SEMENTE)
    y_ref = calcular_referencia(A, x)

    resultados = {}
    for n in LARGURAS:
        resultados[f"T{n}"] = erro_relativo(executar_takum(A, x, n), y_ref)
        resultados[f"FP{n}"] = erro_relativo(calcular_padrao(A, x, n), y_ref)

    imprimir_tabela({nome: (resumir(e), excl) for nome, (e, excl) in resultados.items()})


if __name__ == "__main__":
    main()