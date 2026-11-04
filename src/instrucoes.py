"""
instrucoes.py
Executores das instruções. Todos têm a assinatura  exec_x(m, c)  em que
m é a Maquina e c é o dicionário de campos devolvido por identificar().
Devolvem True se alteraram o PC (desvios); caso contrário, o PC avança +4.
"""
from estruturas import Maquina, VLEN
from codificacao import InstrucaoIlegal
from calculos import ula, Op, takum_estreitar, takum_dot


def _verificar_pre_condicoes(m: Maquina, sew_exigido: int | None = None) -> None:
    """Levanta InstrucaoIlegal se vill = 1 ou se o SEW não for permitido."""
    if m.vill:
        raise InstrucaoIlegal("vill = 1: execute vsetvli antes")
    if m.sew not in (8, 16, 32):
        raise InstrucaoIlegal(f"SEW inválido para Takum: {m.sew}")
    if sew_exigido is not None and m.sew != sew_exigido:
        raise InstrucaoIlegal(f"esta instrução exige SEW = {sew_exigido}")


# --- Instruções padrão do RISC-V / RVV --------------------------------------
def exec_vsetvli(m: Maquina, c: dict):
    """vl = min(AVL, VLMAX); grava sew, lmul, vta, vma e vill; rd recebe vl."""
    zimm = c["zimm"]
    vlmul = zimm & 0b111
    vsew = (zimm >> 3) & 0b111              # 000 = 8, 001 = 16, 010 = 32
    vta = bool((zimm >> 6) & 1)
    vma = bool((zimm >> 7) & 1)

    if vlmul != 0 or vsew > 2:              # projeto: LMUL = 1 e SEW em {8, 16, 32}
        m.vill = True
        m.vl = 0
        m.escrever_escalar(c["rd"], 0)
        return False

    m.sew = 8 << vsew
    m.lmul = 1
    m.vta, m.vma = vta, vma
    m.vill = False

    if c["rs1"] != 0:                       # AVL vem do registrador rs1
        m.vl = min(m.ler_escalar(c["rs1"]), m.vlmax())
    elif c["rd"] != 0:                      # rs1 = x0 e rd != x0: AVL = infinito
        m.vl = m.vlmax()
    # rs1 = rd = x0: mantém o vl atual (só muda o vtype)

    m.escrever_escalar(c["rd"], m.vl)       # rd = x0 ignora a escrita
    return False


def _exec_vle(m: Maquina, c: dict, eew: int):
    """Carrega vl elementos de eew bits (little-endian) da memória em vd."""
    _verificar_pre_condicoes(m, sew_exigido=eew)
    n = eew // 8
    base = m.ler_escalar(c["rs1"])
    dados = m.ler_memoria(base, m.vl * n)
    for i in range(m.vl):
        valor = int.from_bytes(dados[i * n:(i + 1) * n], "little")
        m.escrever_elemento(c["vd"], i, valor, sew=eew)
    return False


def _exec_vse(m: Maquina, c: dict, eew: int):
    """Grava vl elementos de eew bits de vs3 na memória."""
    # eew = largura efetiva do elemento, aqui eew = sew

    _verificar_pre_condicoes(m, sew_exigido=eew)
    n = eew // 8                                # divide por 8 e descarta a parte decimal, quantos bytes cada elemento ocupa
    base = m.ler_escalar(c["rs1"])
    dados = bytearray()
    for i in range(m.vl):
        dados += m.ler_elemento(c["vs3"], i, sew=eew).to_bytes(n, "little")
    m.escrever_memoria(base, bytes(dados))
    return False


def exec_addi(m: Maquina, c: dict):
    m.escrever_escalar(c["rd"], m.ler_escalar(c["rs1"]) + c["imm"])
    return False


def exec_bne(m: Maquina, c: dict):
    """Se rs1 != rs2, m.pc += imediato e devolve True."""
    if m.ler_escalar(c["rs1"]) != m.ler_escalar(c["rs2"]):
        m.pc += c["imm"]
        return True
    return False


# --- Instruções Zvtakum (proposta) -------------------------------------------
def exec_vtadd(m: Maquina, c: dict):
    """vd[i] = ula(ADD, vs2[i], vs1[i], SEW)"""
    _verificar_pre_condicoes(m)
    for i in range(m.vl):                     
        a = m.ler_elemento(c["vs2"], i)        
        b = m.ler_elemento(c["vs1"], i)
        r = ula(Op.ADD, a, b, m.sew)               
        m.escrever_elemento(c["vd"], i, r)     


def exec_vtsub(m: Maquina, c: dict):
    """vd[i] = ula(SUB, vs2[i], vs1[i], SEW)"""
    _verificar_pre_condicoes(m)
    for i in range(m.vl):                     
        a = m.ler_elemento(c["vs2"], i)        
        b = m.ler_elemento(c["vs1"], i)
        r = ula(Op.SUB, a, b, m.sew)               
        m.escrever_elemento(c["vd"], i, r)     


def exec_vtmul(m: Maquina, c: dict):
    """vd[i] = ula(MUL, vs2[i], vs1[i], SEW)"""
    _verificar_pre_condicoes(m)
    for i in range(m.vl):                     
        a = m.ler_elemento(c["vs2"], i)        
        b = m.ler_elemento(c["vs1"], i)
        r = ula(Op.MUL, a, b, m.sew)               
        m.escrever_elemento(c["vd"], i, r)   


def _exec_vtdot(m: Maquina, c: dict, n: int):
    _verificar_pre_condicoes(m, sew_exigido=32)
    if m.vl == 0:
        return False                                   # nada a calcular
    k = 32 // n
    a = [m.ler_elemento(c["vs2"], i, sew=n) for i in range(m.vl * k)]
    b = [m.ler_elemento(c["vs1"], i, sew=n) for i in range(m.vl * k)]
    acc = m.ler_elemento(c["vd"], 0, sew=32)
    r = takum_dot(acc, a, b, n)
    m.escrever_elemento(c["vd"], 0, r, sew=32)         # só a lane 0 de vd
    return False


def exec_vtdot8(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 8)


def exec_vtdot16(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 16)


def exec_vtdot32(m: Maquina, c: dict):
    return _exec_vtdot(m, c, 32)


def exec_vncvt(m: Maquina, c: dict):
    _verificar_pre_condicoes(m)
    if m.sew == 32:
        raise InstrucaoIlegal("vncvt.t.t: não existe fonte de 64 bits")
    if c["vs2"] % 2 != 0:
        raise InstrucaoIlegal("vncvt.t.t: vs2 deve ser par (grupo de 2 registradores)")

    n_dst, n_src = m.sew, 2 * m.sew
    por_reg = VLEN // n_src                       # elementos largos por registrador
    for i in range(m.vl):
        reg = c["vs2"] + i // por_reg             # a fonte pode ocupar vs2 e vs2+1
        a = m.ler_elemento(reg, i % por_reg, sew=n_src)
        r = takum_estreitar(a, n_src, n_dst)
        m.escrever_elemento(c["vd"], i, r)        # sew = m.sew
    return False


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
