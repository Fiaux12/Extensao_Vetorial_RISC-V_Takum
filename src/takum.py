"""
takum.py  (Fase 1, item 1)
Codificação e decodificação do formato Takum (variante logarítmica).

Todas as funções recebem/devolvem PADRÕES DE BITS como inteiros sem sinal de
n bits (n = 8, 16 ou 32). Detalhes e fórmulas: artigo do Hunhold [2].
"""


def nar(n: int) -> int:
    """Padrão do NaR (Not a Real): 1000...0."""
    return 1 << (n - 1)


def eh_nar(bits: int, n: int) -> bool:
    return bits == nar(n)


def eh_zero(bits: int, n: int) -> bool:
    return bits == 0


def float_para_takum(valor: float, n: int) -> int:
    """float -> padrão de bits Takum de n bits (com arredondamento)."""
    raise NotImplementedError


def takum_para_float(bits: int, n: int) -> float:
    """Padrão Takum de n bits -> float. Para a referência de alta precisão
    (erro relativo vs Float128), converter para mpmath em vez de float."""
    raise NotImplementedError


def decodificar_takum(bits: int, n: int):
    """Extrai os campos: sinal S, direção D, regime R, característica C, fração F.

    Devolve, para a variante logarítmica, o sinal e o logaritmo ell em ponto
    fixo (e os campos, se forem úteis para depuração).
    A decodificação comum usa no máximo os 12 bits mais significativos.
    """
    raise NotImplementedError


def codificar_takum(sinal: int, ell, n: int) -> int:
    """(sinal, ell) -> padrão de bits de n bits.
    Inclui arredondamento ao mais próximo (empate para o par) e saturação.
    """
    raise NotImplementedError
