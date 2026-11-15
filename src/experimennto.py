"""
experimento.py
Fase 3: y = A . x no Takum (executado no simulador) e no padrão IEEE
(FP8/FP16/FP32, aproximado em Python), com o erro relativo de cada um
medido contra uma referência em precisão alta.

Executar:  python experimento.py
"""
import math
import random
import sys
from decimal import Decimal, localcontext

import numpy as np

from estruturas import Maquina, VLEN, TAM_MEMORIA
from codificacao import montar
from takum import float_para_takum, takum_para_float
from main import executar
from graficos import gerar_graficos_por_tamanho

# --- Parâmetros do experimento ----------------------------------------------
LINHAS = 16
COLUNAS = 32
ESPARSIDADE = 0.7           # fração de zeros em A
SEMENTE = 42
LARGURAS = (8, 16, 32)      # T8/T16/T32 e FP8/FP16/FP32

# --- Memória do simulador -------------------------------------------------------
# A matriz (linhas uma após a outra), x, o acumulador zerado e o vetor y ficam
# em regiões consecutivas; os endereços são calculados por layout_takum().

# --- FP8: (bits de expoente, bits de mantissa, bias, maior valor finito) ------
FP8 = (4, 3, 7, 448.0)      # E4M3. Para E5M2 use (5, 2, 15, 57344.0)

# =============================================================================
# 1. Dados e referência
# =============================================================================
def gerar_dados(linhas: int, colunas: int, esparsidade: float, semente: int):
    """Devolve (A, x): A como lista de listas de float, com a fração
    `esparsidade` de zeros; x como lista de float. Usa random com semente fixa."""
    rng = random.Random(semente)               # gerador próprio: não mexe no random global

    def valor():
        return rng.uniform(0.0, 1.0)

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
    """Quantos elementos de n bits cabem em um pedaço processado por UM vtdot:
    4 lanes de 32 bits (VLEN = 128) x (32 // n) elementos por lane."""
    if n not in (8, 16, 32):
        raise ValueError(f"largura inválida: {n}")
    lanes = VLEN // 32                 
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


def layout_takum(linhas: int, colunas: int, n: int) -> dict:
    """Endereços (bytes) de cada região da memória para uma matriz linhas x colunas
    em T<n>: A (linha após linha, cada uma completada com zeros até um múltiplo
    do pedaço), x, acumulador zerado (1 registrador vetorial) e y (T32 por linha)."""
    ped = pedaco_elementos(n)
    n_pedacos = -(-colunas // ped)                    # divisão para cima
    total = n_pedacos * ped                           # elementos por linha, com preenchimento
    stride = total * (n // 8)                         # bytes por linha
    end_a = 0
    end_x = end_a + linhas * stride
    end_acc = end_x + stride
    end_y = end_acc + VLEN // 8
    if end_y + 4 * linhas > TAM_MEMORIA:
        raise ValueError("matriz grande demais para a memória do simulador")
    return {"n": n, "linhas": linhas, "colunas": colunas, "n_pedacos": n_pedacos,
            "ped": ped, "total": total, "stride": stride,
            "end_a": end_a, "end_x": end_x, "end_acc": end_acc, "end_y": end_y}


def carregar_dados_takum(m: Maquina, A: list, x: list, n: int) -> dict:
    """Grava A (todas as linhas) e x na memória como vetores Takum de n bits.
    Devolve o layout usado."""
    L = layout_takum(len(A), len(x), n)
    for i, linha in enumerate(A):
        escrever_vetor_na_memoria(m, L["end_a"] + i * L["stride"], linha, n, L["total"])
    escrever_vetor_na_memoria(m, L["end_x"], x, n, L["total"])
    return L


def executar_takum_linha(m: Maquina, i: int, L: dict) -> float:
    """Roda a linha i de A (já na memória) e devolve y[i], lido da memória."""
    end_y = L["end_y"] + 4 * i
    for reg, endereco in ((10, L["end_a"] + i * L["stride"]),    # a0 = linha i de A
                          (11, L["end_x"]),                       # a1 = x
                          (12, L["end_acc"]),                     # a2 = acumulador (zero)
                          (13, end_y)):                           # a3 = destino de y[i]
        m.escrever_escalar(reg, endereco)
    m.carregar_programa(montar_programa_linha(L["n"], L["n_pedacos"]))
    executar(m)
    bits = int.from_bytes(m.ler_memoria(end_y, 4), "little")      # y[i] é um T32
    return takum_para_float(bits, 32)


def simular_takum(A: list, x: list, n: int):
    """Devolve (m, y, L): a máquina depois da execução (com tudo na memória),
    os resultados lidos da memória e o layout."""
    m = Maquina()
    L = carregar_dados_takum(m, A, x, n)
    y = [executar_takum_linha(m, i, L) for i in range(len(A))]
    return m, y, L


def executar_takum(A: list, x: list, n: int) -> list:
    """y = A . x em T<n> (só os resultados)."""
    return simular_takum(A, x, n)[1]


# =============================================================================
# 3. Lado padrão IEEE (aproximado em Python)
# =============================================================================
def _arredondar_minifloat(v: float, exp_bits: int, man_bits: int, bias: int,
                          maximo: float) -> float:
    """Arredonda v para o ponto flutuante de poucos bits (ao mais próximo, empate
    para par). Subnormais incluídos. Fora da faixa, satura no maior valor finito."""
    if v == 0.0 or math.isnan(v):
        return v
    sinal = -1.0 if v < 0 else 1.0
    a = abs(v)
    if a >= maximo:
        return sinal * maximo
    e = math.frexp(a)[1] - 1                  # a = m * 2^e, com m em [1, 2)
    e = max(e, 1 - bias)                      # subnormais usam o menor expoente
    passo = 2.0 ** (e - man_bits)             # distância entre valores vizinhos
    return sinal * min(round(a / passo) * passo, maximo)   # round() de int: empate par


def quantizar_ieee(valor: float, n: int) -> float:
    """Arredonda para FP<n> e devolve como float. FP16/FP32: numpy.
    FP8: arredondamento manual (_arredondar_minifloat), sem biblioteca extra."""
    if n == 32:
        return float(np.float32(valor))
    if n == 16:
        return float(np.float16(valor))
    if n == 8:
        return _arredondar_minifloat(valor, *FP8)
    raise ValueError(f"largura inválida: {n}")


def calcular_padrao(A: list, x: list, n: int) -> list:
    """y = A . x com A e x guardados em FP<n> (quantizar_ieee). Os produtos e o
    acumulador são FP32 e a soma é arredondada a cada passo (como o vtdot, que
    acumula em T32). Laço explícito: nada de sum() ou np.dot."""
    xq = [quantizar_ieee(v, n) for v in x]
    y = []
    for linha in A:
        acc = np.float32(0.0)
        for a, xj in zip(linha, xq):
            produto = np.float32(quantizar_ieee(a, n)) * np.float32(xj)
            acc = np.float32(acc + produto)             # arredonda a cada soma
        y.append(float(acc))
    return y


# =============================================================================
# 4. Erro e relatório
# =============================================================================
def _erro_linha(yi: float, ref: Decimal):
    """Erro relativo de uma linha; None se y_ref == 0. NaN/inf (ex.: NaR) = infinito."""
    if ref == 0:
        return None
    if math.isnan(yi) or math.isinf(yi):
        return math.inf
    return float(abs(Decimal(yi) - ref) / abs(ref))          # Decimal(float) é exato


def erro_relativo(y: list, y_ref: list):
    """Devolve (erros, n_excluidos): |y - y_ref| / |y_ref| por linha,
    excluindo (e contando) as linhas com y_ref == 0."""
    erros, excluidos = [], 0
    for yi, ref in zip(y, y_ref):
        e = _erro_linha(yi, ref)
        if e is None:
            excluidos += 1
        else:
            erros.append(e)
    return erros, excluidos


def erro_absoluto(y: list, y_ref: list) -> list:
    """|y - y_ref| por linha (definido também quando y_ref == 0).
    NaN/inf (ex.: NaR) conta como erro infinito."""
    return [math.inf if math.isnan(yi) or math.isinf(yi)
            else float(abs(Decimal(yi) - ref))
            for yi, ref in zip(y, y_ref)]


def calcular_erros(A: list, x: list, y_ref: list) -> dict:
    """Roda todos os formatos e devolve {nome: (erros_abs, erros_rel, excluidas)}."""
    resultados = {}
    for w in LARGURAS:
        for nome, y in ((f"T{w}", executar_takum(A, x, w)),
                        (f"FP{w}", calcular_padrao(A, x, w))):
            erros_rel, excluidas = erro_relativo(y, y_ref)
            resultados[nome] = (erro_absoluto(y, y_ref), erros_rel, excluidas)
    return resultados


def resumir(erros: list) -> dict:
    """Mediana, percentil 95 e máximo dos erros."""
    if not erros:
        return {"mediana": math.nan, "p95": math.nan, "maximo": math.nan}
    return {"mediana": float(np.median(erros)),
            "p95": float(np.percentile(erros, 95)),
            "maximo": max(erros)}


def imprimir_tabela(resultados: dict, descricao: str = "") -> None:
    """`resultados` é {nome: (erros_abs, erros_rel, excluidas)}."""
    print(f"\nErro de y = A.x contra a referência ({descricao})")
    print(f"{'Formato':<8}{'Erro abs.':>13}{'Erro rel.':>13}{'Mediana abs.':>15}{'Rel. excl.':>12}")
    print(f"{'':<8}{'(média)':>13}{'(média)':>13}{'':>15}{'(y_ref=0)':>12}")
    print("-" * 61)
    for nome, (abs_, rel, excluidas) in resultados.items():
        media_rel = float(np.mean(rel)) if rel else math.nan
        print(f"{nome:<8}{float(np.mean(abs_)):>13.2e}{media_rel:>13.2e}"
              f"{float(np.median(abs_)):>15.2e}{excluidas:>12}")

# =============================================================================
# 5. Visualização: memória e comparação Takum x padrão
# =============================================================================
def _linhas_memoria(m: Maquina, inicio: int, qtd: int, n: int, originais=None) -> None:
    """Imprime `qtd` elementos de n bits a partir de `inicio`: endereço, binário,
    hex, valor armazenado e (opcional) o valor original."""
    n_bytes = n // 8
    for k in range(qtd):
        end = inicio + k * n_bytes
        bits = int.from_bytes(m.ler_memoria(end, n_bytes), "little")
        texto = (f"  0x{end:04X} | {bits:0{n}b} | 0x{bits:0{n // 4}X} | "
                 f"{takum_para_float(bits, n):>11.5g}")
        if originais is not None:
            orig = f"{originais[k]:>10.5f}" if k < len(originais) else f"{'(preench.)':>10}"
            texto += f" | {orig}"
        print(texto)


def _cabecalho_memoria(com_original: bool) -> None:
    print("  endereço | binário (bits do elemento)    | hex | armazenado"
          + (" | original" if com_original else ""))


def mostrar_dados_na_memoria(m: Maquina, L: dict, A: list, x: list,
                             max_linhas: int = 3) -> None:
    """Mostra como a matriz A e o vetor x estão guardados na memória (Takum)."""
    n = L["n"]
    print(f"\n=== Memória: A ({L['linhas']}x{L['colunas']}) e x em T{n} ===")
    print(f"Cada linha ocupa {L['stride']} bytes = {L['n_pedacos']} pedaço(s) de "
          f"{L['ped']} elementos de {n} bits; o fim é completado com zeros (preench.).")
    for i in range(min(max_linhas, L["linhas"])):
        print(f"\nLinha {i} de A, a partir de 0x{L['end_a'] + i * L['stride']:04X}:")
        _cabecalho_memoria(True)
        _linhas_memoria(m, L["end_a"] + i * L["stride"], L["total"], n, A[i])
    if L["linhas"] > max_linhas:
        print(f"\n... (+{L['linhas'] - max_linhas} linhas de A não exibidas)")
    print(f"\nVetor x, a partir de 0x{L['end_x']:04X}:")
    _cabecalho_memoria(True)
    _linhas_memoria(m, L["end_x"], L["total"], n, x)


def mostrar_resultado_na_memoria(m: Maquina, L: dict) -> None:
    """Mostra o vetor y como o vtdot o deixou na memória (um T32 por linha)."""
    print(f"\n=== Memória: resultado y (T32, 4 bytes por linha), a partir de "
          f"0x{L['end_y']:04X} ===")
    _cabecalho_memoria(False)
    _linhas_memoria(m, L["end_y"], L["linhas"], 32)


def comparar_resultados(y_ref: list, y_takum: list, y_padrao: list, n: int) -> None:
    """Tabela linha a linha: referência, Takum, padrão IEEE e o erro relativo de cada."""
    print(f"\n=== Comparação: T{n} x FP{n} (acumulador FP32) ===")
    print(f"{'linha':<6}{'referência':>13}{f'T{n}':>13}{f'FP{n}':>13}"
          f"{f'erro T{n}':>12}{f'erro FP{n}':>12}  menor erro")
    for i, (ref, yt, yp) in enumerate(zip(y_ref, y_takum, y_padrao)):
        et, ep = _erro_linha(yt, ref), _erro_linha(yp, ref)
        fmt = lambda e: f"{'-':>12}" if e is None else f"{e:>12.2e}"
        melhor = "" if et is None else ("T" if et < ep else "FP" if ep < et else "=")
        print(f"{i:<6}{float(ref):>13.6f}{yt:>13.6f}{yp:>13.6f}{fmt(et)}{fmt(ep)}  {melhor}")


def demonstracao(n: int = 16, linhas: int = 6, colunas: int = 6,
                 esparsidade: float = 0.5, semente: int = 7) -> None:
    """Versão pequena do experimento, mostrando a memória e a comparação."""
    A, x = gerar_dados(linhas, colunas, esparsidade, semente)
    print("A original:")
    for linha in A:
        print("  ", [f"{v:.4f}" for v in linha])

    print("\n")
    print("x original:", [f"{v:.4f}" for v in x])

    m, y_takum, L = simular_takum(A, x, n)
    mostrar_dados_na_memoria(m, L, A, x)
    mostrar_resultado_na_memoria(m, L)
    y_ref = calcular_referencia(A, x)
    comparar_resultados(y_ref, y_takum, calcular_padrao(A, x, n), n)
    print("\n")

    imprimir_tabela(calcular_erros(A, x, y_ref),
                    f"{linhas}x{colunas}, {esparsidade:.0%} de zeros, semente {semente}")


def main() -> None:
    demonstracao(16)
    print("\n")
    
    gerar_graficos_por_tamanho()

if __name__ == "__main__":
    main()


