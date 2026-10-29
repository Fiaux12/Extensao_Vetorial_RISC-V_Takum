"""
calculos.py  (Fase 1, item 2) -- ULA Takum
Operações escalares sobre UM elemento, para n = 8, 16 ou 32.
As instruções vetoriais chamam estas funções uma vez por lane ativa.

Casos especiais: NaR domina; zero não tem sinal;
resultado satura em vez de gerar infinito.
"""
from enum import Enum


class Op(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"


def takum_neg(a: int, n: int) -> int:
    """-a. NaR e zero permanecem iguais."""
    raise NotImplementedError


def takum_add(a: int, b: int, n: int) -> int:
    """a + b. No Takum logarítmico: ordenar por módulo, diferença dos
    logaritmos e correção de Gauss (tabela ou aproximação).
    Caso especial: módulos iguais e sinais opostos -> zero."""
    raise NotImplementedError


def takum_sub(a: int, b: int, n: int) -> int:
    """a - b  =  takum_add(a, takum_neg(b, n), n)."""
    raise NotImplementedError


def takum_mul(a: int, b: int, n: int) -> int:
    """a * b. No logarítmico: sinal = sa XOR sb e ell = ell_a + ell_b."""
    raise NotImplementedError


def takum_alargar(a: int, n_entrada: int, n_saida: int) -> int:
    """Converte para uma largura maior (ex.: T8 -> T32). Deve ser exata."""
    raise NotImplementedError


def takum_estreitar(a: int, n_entrada: int, n_saida: int) -> int:
    """Converte para uma largura menor (ex.: T16 -> T8) com arredondamento
    e saturação. Base da instrução vncvt.t.t."""
    raise NotImplementedError


def takum_dot(acc: int, elems_a: list, elems_b: list, n: int) -> int:
    """acc + soma(a_j * b_j), com os produtos calculados em T32 (sem reduzir
    para n bits) e soma sequencial. n é a largura dos elementos de entrada;
    acc e o resultado são T32."""
    raise NotImplementedError


def ula(op: Op, a: int, b: int, n: int) -> int:
    """Seleciona a operação (sinal de controle) e executa."""
    operacoes = {
        Op.ADD: takum_add,
        Op.SUB: takum_sub,
        Op.MUL: takum_mul,
    }
    return operacoes[op](a, b, n)
