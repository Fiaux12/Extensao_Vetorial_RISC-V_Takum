"""
instrucoes.py
Executores das instruções. Todos têm a assinatura  exec_x(m, c)  em que
m é a Maquina e c é o dicionário de campos devolvido por identificar().
Devolvem True se alteraram o PC (desvios); caso contrário, o PC avança +4.
"""
from estruturas import Maquina
import calculos


def _verificar_pre_condicoes(m: Maquina, sew_exigido: int | None = None) -> None:
    """Levanta InstrucaoIlegal se vill = 1 ou se o SEW não for permitido."""
    raise NotImplementedError


# --- Instruções padrão do RISC-V / RVV --------------------------------------
def exec_vsetvli(m: Maquina, c: dict):
    """vl = min(AVL, VLMAX); grava sew, lmul, vta, vma e vill; rd recebe vl."""
    raise NotImplementedError


def _exec_vle(m: Maquina, c: dict, eew: int):
    """Carrega vl elementos de eew bits (little-endian) da memória em vd."""
    raise NotImplementedError


def _exec_vse(m: Maquina, c: dict, eew: int):
    """Grava vl elementos de eew bits de vs3 na memória."""
    raise NotImplementedError


def exec_addi(m: Maquina, c: dict):
    raise NotImplementedError


def exec_bne(m: Maquina, c: dict):
    """Se rs1 != rs2, m.pc += imediato e devolve True."""
    raise NotImplementedError


# --- Instruções Zvtakum (proposta) -------------------------------------------
def exec_vtadd(m: Maquina, c: dict):
    """para i < vl: vd[i] = ula(ADD, vs2[i], vs1[i], SEW)"""
    raise NotImplementedError


def exec_vtsub(m: Maquina, c: dict):
    """para i < vl: vd[i] = ula(SUB, vs2[i], vs1[i], SEW)"""
    raise NotImplementedError


def exec_vtmul(m: Maquina, c: dict):
    """para i < vl: vd[i] = ula(MUL, vs2[i], vs1[i], SEW)"""
    raise NotImplementedError


def _exec_vtdot(m: Maquina, c: dict, n: int):
    """SEW = 32; vl conta lanes de 32 bits; k = 32 // n elementos por lane.
    para i < vl: vd[i] = takum_dot(vd[i], elems de vs2 e vs1 da lane i, n)"""
    raise NotImplementedError


def exec_vtdot8(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 8)


def exec_vtdot16(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 16)


def exec_vtdot32(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 32)


def exec_vncvt(m: Maquina, c: dict):
    raise NotImplementedError


# --- Tabela de despacho: nome da instrução -> executor ----------------------
TABELA_EXEC = {
    "vsetvli":    exec_vsetvli,
    "vle8.v":     lambda m, c: _exec_vle(m, c, 8),
    "vle16.v":    lambda m, c: _exec_vle(m, c, 16),
    "vle32.v":    lambda m, c: _exec_vle(m, c, 32),
    "vse8.v":     lambda m, c: _exec_vse(m, c, 8),
    "vse16.v":    lambda m, c: _exec_vse(m, c, 16),
    "vse32.v":    lambda m, c: _exec_vse(m, c, 32),
    "addi":       exec_addi,
    "bne":        exec_bne,
    "vtadd.vv":   exec_vtadd,
    "vtsub.vv":   exec_vtsub,
    "vtmul.vv":   exec_vtmul,
    "vtdot8.vv":  exec_vtdot8,
    "vtdot16.vv": exec_vtdot16,
    "vtdot32.vv": exec_vtdot32,
    "vncvt.t.t":  exec_vncvt,
}
