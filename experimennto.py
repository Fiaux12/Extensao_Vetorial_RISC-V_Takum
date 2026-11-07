"""
experimento.py
Fase 3: y = A . x no Takum (executado no simulador) e no padrão IEEE
(FP8/FP16/FP32, aproximado em Python), com o erro relativo de cada um
medido contra uma referência em precisão alta.

Executar:  python experimento.py
"""
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
    raise NotImplementedError


def calcular_referencia(A: list, x: list) -> list:
    """y_ref = A . x em precisão alta, a partir dos valores originais
    (float do Python ou decimal)."""
    raise NotImplementedError


# =============================================================================
# 2. Lado Takum (executado no simulador)
# =============================================================================
def pedaco_elementos(n: int) -> int:
    """Quantos elementos de n bits cabem em um pedaço processado por UM vtdot:
    4 lanes de 32 bits (VLEN = 128) x (32 // n) elementos por lane."""
    raise NotImplementedError


def escrever_vetor_na_memoria(m: Maquina, endereco: int, valores: list, n: int,
                              tamanho_total: int) -> None:
    """Converte cada valor para Takum de n bits e grava na memória (little-endian),
    completando com zeros até `tamanho_total` elementos."""
    raise NotImplementedError


def montar_programa_linha(n: int, n_pedacos: int) -> list:
    """Programa de uma linha: para cada pedaço, vle32.v (A), vle32.v (x),
    vtdotN.vv acumulando em v3[0]; ao final, vse32.v do escalar.
    Os endereços ficam nos registradores a0..a3 (definidos pelo Python)."""
    raise NotImplementedError


def executar_takum_linha(m: Maquina, linha: list, x: list, n: int) -> float:
    """Roda uma linha de A no simulador e devolve y[i] (float, decodificado)."""
    raise NotImplementedError


def executar_takum(A: list, x: list, n: int) -> list:
    """y = A . x em T<n>: uma linha por vez, com Maquina nova a cada linha."""
    raise NotImplementedError


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