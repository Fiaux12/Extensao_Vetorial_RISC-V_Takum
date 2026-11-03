"""
n bits (n = 8, 16 ou 32)
T = S D R C M      
S, D: 1 bit;  R: 3 bits;  C: r bits;  M: p = n - r - 5 bits

r = R (D = 1)  ou  7 - R (D = 0)
c = 2^r - 1 + C (D = 1)  ou  -2^(r+1) + 1 + C (D = 0)        c em [-255, 254]
m = M / 2^p em [0, 1)
ell_barra = c + m  
ell = (−1)^S · (c + m)
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class TakumDecodificado:
    n: int
    zero: bool = False
    nar: bool = False
    sinal: int = 0              # S
    direcao: int = 0            # D
    regime: int = 0             # r (valor do regime, 0..7)
    caracteristica: int = 0     # c (-255..254)
    n_mantissa: int = 0         # p, bits reais de mantissa (0 se C foi cortado)
    mantissa: int = 0           # M, como inteiro de p bits
    frac: int = 0               # bits fracionários dos valores abaixo
    ell_barra: int = 0          # c + m, ponto fixo com `frac` bits
    ell: int = 0                # (-1)^S * (c + m), ponto fixo com `frac` bits


def nar(n: int) -> int:
    """Padrão do NaR (Not a Real): 1000...0."""
    return 1 << (n - 1)


def eh_nar(bits: int, n: int) -> bool:
    return bits == nar(n)


def eh_zero(bits: int, n: int) -> bool:
    return bits == 0


def bits_fracao_padrao(n: int) -> int:
    """Bits fracionários da representação interna: n - 5 (mínimo 0)."""
    return max(n - 5, 0)


def decodificar_takum(bits: int, n: int) -> TakumDecodificado:
    """Extrai S, D, R, C, M e calcula c, m e o logaritmo em ponto fixo.

    Zero e NaR são sinalizados em `zero` e `nar` (os demais campos ficam em 0).
    A decodificação só precisa dos 12 bits mais significativos: o padrão é
    estendido com zeros até 12 bits quando n < 12.
    """
    if not 2 <= n <= 64:
        raise ValueError("n deve estar entre 2 e 64")
    if not 0 <= bits < (1 << n):
        raise ValueError(f"o padrão não cabe em {n} bits")

    frac = bits_fracao_padrao(n)
    s = bits >> (n - 1)

    # D = R = C = M = 0: zero (S = 0) ou NaR (S = 1)
    if bits & ((1 << (n - 1)) - 1) == 0:
        return TakumDecodificado(n=n, zero=(s == 0), nar=(s == 1),
                                 sinal=s, frac=frac)

    L = max(n, 12)
    t = bits << (L - n)                          # bits fantasmas = 0
    d = (t >> (L - 2)) & 1
    reg = (t >> (L - 5)) & 0b111
    r = reg if d else 7 - reg
    car = (t >> (L - 5 - r)) & ((1 << r) - 1)    # r bits (os cortados valem 0)
    p_ext = L - r - 5
    m_ext = t & ((1 << p_ext) - 1)

    if d == 0:
        c = -(1 << (r + 1)) + 1 + car
    else:
        c = (1 << r) - 1 + car

    # parte fracionária de ell_barra com `frac` bits (exata)
    if frac >= p_ext:
        parte_frac = m_ext << (frac - p_ext)
    else:
        parte_frac = m_ext >> (p_ext - frac)

    n_mant = max(n - r - 5, 0)
    ell_barra = (c << frac) + parte_frac
    ell = -ell_barra if s else ell_barra

    return TakumDecodificado(
        n=n, sinal=s, direcao=d, regime=r, caracteristica=c,
        n_mantissa=n_mant, mantissa=m_ext >> (p_ext - n_mant),
        frac=frac, ell_barra=ell_barra, ell=ell)


def codificar_takum(sinal: int, ell: int, n: int, frac: int | None = None) -> int:

    if not 2 <= n <= 64:
        raise ValueError("n deve estar entre 2 e 64")
    if sinal not in (0, 1):
        raise ValueError("sinal deve ser 0 ou 1")
    if frac is None:
        frac = bits_fracao_padrao(n)
    if frac < 0:
        raise ValueError("frac deve ser >= 0")

    mascara_baixa = (1 << (n - 1)) - 1           # os n-1 bits depois do sinal
    ell_barra = -ell if sinal else ell

    # saturação fora da faixa aberta (-255, 255)
    limite = 255 << frac
    if ell_barra >= limite:
        return (sinal << (n - 1)) | mascara_baixa
    if ell_barra <= -limite:
        return (sinal << (n - 1)) | 1

    c = ell_barra >> frac                        # piso: -255 ... 254
    f = ell_barra & ((1 << frac) - 1)            # parte fracionária (frac bits)

    # direção, regime e bits da característica
    if c >= 0:
        d = 1
        r = (c + 1).bit_length() - 1
        reg = r
        car = c + 1 - (1 << r)
    else:
        d = 0
        r = (-c).bit_length() - 1
        reg = 7 - r
        car = c + (1 << (r + 1)) - 1

    # cadeia estendida S D R C M (M = f, com `frac` bits)
    cadeia = (sinal << 1) | d
    cadeia = (cadeia << 3) | reg
    cadeia = (cadeia << r) | car
    cadeia = (cadeia << frac) | f
    comprimento = 5 + r + frac

    desloc = comprimento - n
    if desloc > 0:
        truncado = cadeia >> desloc
        resto = cadeia & ((1 << desloc) - 1)
        meio = 1 << (desloc - 1)
    else:                                        # cadeia mais curta: completa com zeros
        truncado = cadeia << (-desloc)
        resto, meio = 0, 1

    baixo = truncado & mascara_baixa
    if baixo == 0:                               # truncar daria 0 ou NaR
        baixo = 1
    elif baixo == mascara_baixa:                 # subir daria NaR ou 0
        pass
    elif resto > meio or (resto == meio and (baixo & 1)):
        baixo += 1                               # ao mais próximo, empate par

    return (sinal << (n - 1)) | baixo


def float_para_takum(valor: float, n: int) -> int:
    if not 2 <= n <= 64:
        raise ValueError("n deve estar entre 2 e 64")
    if math.isnan(valor) or math.isinf(valor):
        return nar(n)
    if valor == 0.0:
        return 0

    s = 1 if valor < 0 else 0
    ell = 2.0 * math.log(abs(valor))
    ell_fx = math.floor(ell * (1 << 64))         # multiplicação por 2^64 é exata
    return codificar_takum(s, ell_fx, n, frac=64)


def takum_para_float(bits: int, n: int) -> float:
    d = decodificar_takum(bits, n)
    if d.zero:
        return 0.0
    if d.nar:
        return math.nan
    ell = d.ell / (1 << d.frac)                  # divisão exata (potência de 2)
    return (-1.0) ** d.sinal * math.exp(ell / 2.0)