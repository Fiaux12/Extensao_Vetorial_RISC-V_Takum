"""
Operações escalares sobre UM elemento, para n = 8, 16 ou 32.
As instruções vetoriais chamam estas funções uma vez por lane ativa.

Casos especiais: NaR domina; zero não tem sinal;
resultado satura em vez de gerar infinito.
"""
import math
from enum import Enum
from takum import decodificar_takum, codificar_takum, nar, eh_nar, eh_zero

# bits de guarda
G = 8

class Op(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"


def takum_neg(a: int, n: int) -> int:
    """-a. NaR e zero permanecem iguais."""
    return (-a) & ((1 << n) - 1)


def takum_add(a: int, b: int, n: int) -> int:
    """a + b no domínio logarítmico, com correção de Gauss via math.log."""
    if eh_nar(a, n) or eh_nar(b, n):
        return nar(n)
    if eh_zero(a, n):
        return b
    if eh_zero(b, n):
        return a

    x, y = decodificar_takum(a, n), decodificar_takum(b, n)
    if x.ell < y.ell:                       # ordena pelo módulo
        x, y = y, x
    d = x.ell - y.ell                       # >= 0, com x.frac bits fracionários
    opostos = x.sinal != y.sinal
    if opostos and d == 0:
        return 0                            # módulos iguais, sinais opostos

    dv = d / (1 << x.frac)                  # d como float
    if opostos:
        corr = 2.0 * math.log(-math.expm1(-dv / 2.0))   # 2 ln(1 - e^(-d/2))
    else:
        corr = 2.0 * math.log1p(math.exp(-dv / 2.0))    # 2 ln(1 + e^(-d/2))

    frac = x.frac + G
    ell = (x.ell << G) + round(corr * (1 << frac) )
    return codificar_takum(x.sinal, ell, n, frac=frac)

def takum_sub(a: int, b: int, n: int) -> int:
    return takum_add(a, takum_neg(b, n), n)


def takum_mul(a: int, b: int, n: int) -> int:
    """a * b. No logarítmico: sinal = sa XOR sb e ell = ell_a + ell_b."""
    if eh_nar(a, n) or eh_nar(b, n):
        return nar(n)
    
    if eh_zero(a, n) or eh_zero(b, n):
        return 0
    
    da = decodificar_takum(a, n)
    db = decodificar_takum(b, n)
    s = da.sinal ^ db.sinal
    return codificar_takum(s, da.ell + db.ell, n, frac=da.frac)

def _converter(a: int, n_entrada: int, n_saida: int) -> int:
    if eh_nar(a, n_entrada):
        return nar(n_saida)
    
    if eh_zero(a, n_entrada):
        return 0
    
    d = decodificar_takum(a, n_entrada)
    return codificar_takum(d.sinal, d.ell, n_saida, frac=d.frac)

def takum_alargar(a: int, n_entrada: int, n_saida: int) -> int:
    """Converte para uma largura maior (ex.: T8 -> T32). Deve ser exata."""
    return _converter(a, n_entrada, n_saida) 


def takum_estreitar(a: int, n_entrada: int, n_saida: int) -> int:
    """Converte para uma largura menor (ex.: T16 -> T8) com arredondamento e saturação."""
    return _converter(a, n_entrada, n_saida)    


def takum_dot(acc: int, elems_a: list, elems_b: list, n: int) -> int:
    for ea, eb in zip(elems_a, elems_b):
        pa = takum_alargar(ea, n, 32)
        pb = takum_alargar(eb, n, 32)
        prod = ula(Op.MUL, pa, pb, 32)
        acc = ula(Op.ADD, acc, prod, 32)
    return acc


def ula(op: Op, a: int, b: int, n: int) -> int:
    """Seleciona a operação (sinal de controle) e executa."""
    operacoes = {
        Op.ADD: takum_add,
        Op.SUB: takum_sub,
        Op.MUL: takum_mul,
    }
    return operacoes[op](a, b, n)
