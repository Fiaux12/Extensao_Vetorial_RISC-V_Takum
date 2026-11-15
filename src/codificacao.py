"""
Palavra de 32 bits <-> campos da instrução (montador e decodificador de controle).

Formato OP-V do RVV, usado pela Zvtakum no espaço custom-1:
 31:26 funct6 | 25 vm | 24:20 vs2 | 19:15 vs1 | 14:12 funct3 | 11:7 vd | 6:0 opcode
"""

# --- Opcodes ----------------------------------------------------------------
OPCODE_CUSTOM1 = 0b0101011      
FUNCT3_VV = 0b001

# Instruções padrão que o simulador também precisa reconhecer
OPCODE_OPV = 0b1010111          # vsetvli (funct3 = 111)
OPCODE_LOAD_FP = 0b0000111      # vle8/16/32.v
OPCODE_STORE_FP = 0b0100111     # vse8/16/32.v
OPCODE_OP_IMM = 0b0010011       # addi
OPCODE_BRANCH = 0b1100011       # bne

# --- funct6 das instruções Zvtakum  --------
FUNCT6_VT = {
    "vtadd.vv":   0b000000,
    "vtsub.vv":   0b000010,
    "vtmul.vv":   0b100100,
    "vncvt.t.t":  0b010010,     # vs1 = 10100 (sub-opcode)
    "vtdot8.vv":  0b101100,
    "vtdot16.vv": 0b101101,
    "vtdot32.vv": 0b101110,
}
NOME_POR_FUNCT6 = {f: nome for nome, f in FUNCT6_VT.items()}

# vncvt.t.t tem uma única fonte (vs2): o campo vs1 não é registrador, é um
# sub-opcode, como na vfncvt. 10100 é o valor da vfncvt.f.f.w (float -> float).
VS1_VNCVT = 0b10100
_WIDTH_EEW = {8: 0b000, 16: 0b101, 32: 0b110}
_EEW_POR_WIDTH = {w: e for e, w in _WIDTH_EEW.items()}

class InstrucaoIlegal(Exception):
    pass


def codificar_vt(nome: str, vd: int, vs2: int, vs1: int | None = None,
                 vm: int = 1) -> int:
    """Monta a palavra de 32 bits de uma instrução Zvtakum.
    Para vncvt.t.t, vs1 é o sub-opcode (fixo em VS1_VNCVT)."""
    if nome == "vncvt.t.t":
        if vs1 not in (None, VS1_VNCVT):
            raise ValueError("em vncvt.t.t, vs1 é o sub-opcode 10100")
        vs1 = VS1_VNCVT
    elif vs1 is None:
        raise ValueError(f"{nome} precisa de vs1")
    return ((FUNCT6_VT[nome] << 26) | (vm << 25) | (vs2 << 20) |
            (vs1 << 15) | (FUNCT3_VV << 12) | (vd << 7) | OPCODE_CUSTOM1)


def decodificar_campos(palavra: int) -> dict:
    """Separa os campos do formato OP-V."""
    return {
        "opcode": palavra & 0x7F,
        "vd":     (palavra >> 7) & 0x1F,
        "funct3": (palavra >> 12) & 0x7,
        "vs1":    (palavra >> 15) & 0x1F,
        "vs2":    (palavra >> 20) & 0x1F,
        "vm":     (palavra >> 25) & 0x1,
        "funct6": (palavra >> 26) & 0x3F,
    }


def _reg(v: int) -> int:
    if not 0 <= v <= 31:
        raise ValueError(f"registrador inválido: {v}")
    return v


def _formato_v(funct6, vm, vs2, vs1, funct3, vd, opcode) -> int:
    return ((funct6 << 26) | (vm << 25) | (_reg(vs2) << 20) | (_reg(vs1) << 15) |
            (funct3 << 12) | (_reg(vd) << 7) | opcode)


def _formato_i(imm, rs1, funct3, rd, opcode) -> int:
    if not -2048 <= imm <= 2047:
        raise ValueError(f"imediato não cabe em 12 bits: {imm}")
    return (((imm & 0xFFF) << 20) | (_reg(rs1) << 15) | (funct3 << 12) |
            (_reg(rd) << 7) | opcode)


def _formato_b(imm, rs2, rs1, funct3, opcode) -> int:
    if imm % 2 or not -4096 <= imm <= 4094:
        raise ValueError(f"deslocamento de desvio inválido: {imm}")
    i = imm & 0x1FFF
    return ((((i >> 12) & 1) << 31) | (((i >> 5) & 0x3F) << 25) | (_reg(rs2) << 20) |
            (_reg(rs1) << 15) | (funct3 << 12) | (((i >> 1) & 0xF) << 8) |
            (((i >> 11) & 1) << 7) | opcode)


def codificar(nome: str, *ops, vm: int = 1) -> int:
    def esperar(k):
        if len(ops) != k:
            raise ValueError(f"{nome} espera {k} operandos, recebeu {len(ops)}")

    if nome in FUNCT6_VT:
        if nome == "vncvt.t.t":
            esperar(2)
            vd, vs2 = ops
            vs1 = VS1_VNCVT
        else:
            esperar(3)
            vd, vs2, vs1 = ops
        return _formato_v(FUNCT6_VT[nome], vm, vs2, vs1, FUNCT3_VV, vd, OPCODE_CUSTOM1)
    if nome == "vsetvli":
        esperar(3)
        rd, rs1, zimm = ops
        return (zimm << 20) | (_reg(rs1) << 15) | (0b111 << 12) | (_reg(rd) << 7) | OPCODE_OPV
    if nome.startswith(("vle", "vse")) and nome.endswith(".v"):
        esperar(2)
        eew = int(nome[3:-2])
        if eew not in _WIDTH_EEW:
            raise ValueError(f"EEW inválido em {nome}")
        reg, rs1 = ops
        opcode = OPCODE_LOAD_FP if nome.startswith("vle") else OPCODE_STORE_FP
        return _formato_v(0, 1, 0, rs1, _WIDTH_EEW[eew], reg, opcode)
    if nome == "addi":
        esperar(3)
        rd, rs1, imm = ops
        return _formato_i(imm, rs1, 0b000, rd, OPCODE_OP_IMM)
    if nome == "bne":
        esperar(3)
        rs1, rs2, imm = ops
        return _formato_b(imm, rs2, rs1, 0b001, OPCODE_BRANCH)
    raise ValueError(f"instrução desconhecida: {nome}")


def _com_sinal(v: int, bits: int) -> int:
    return v - (1 << bits) if v >> (bits - 1) else v


def _identificar_padrao(palavra: int, c: dict):
    op, f3 = c["opcode"], c["funct3"]
    if op == OPCODE_OPV and f3 == 0b111 and (palavra >> 31) == 0:
        return "vsetvli", {"rd": c["vd"], "rs1": c["vs1"], "zimm": (palavra >> 20) & 0x7FF}
    if op in (OPCODE_LOAD_FP, OPCODE_STORE_FP) and f3 in _EEW_POR_WIDTH:
        if c["vm"] != 1 or c["vs2"] != 0 or c["funct6"] != 0:
            raise InstrucaoIlegal("só vle/vse unit-stride sem máscara")
        eew = _EEW_POR_WIDTH[f3]
        if op == OPCODE_LOAD_FP:
            return f"vle{eew}.v", {"vd": c["vd"], "rs1": c["vs1"]}
        return f"vse{eew}.v", {"vs3": c["vd"], "rs1": c["vs1"]}
    if op == OPCODE_OP_IMM and f3 == 0b000:
        return "addi", {"rd": c["vd"], "rs1": c["vs1"], "imm": _com_sinal(palavra >> 20, 12)}
    if op == OPCODE_BRANCH and f3 == 0b001:
        imm = (((palavra >> 31) & 1) << 12) | (((palavra >> 7) & 1) << 11) | \
              (((palavra >> 25) & 0x3F) << 5) | (((palavra >> 8) & 0xF) << 1)
        return "bne", {"rs1": c["vs1"], "rs2": c["vs2"], "imm": _com_sinal(imm, 13)}
    raise InstrucaoIlegal(f"instrução não suportada: 0x{palavra:08x}")


def identificar(palavra: int):
    """Unidade de controle: devolve (nome da instrução, campos)."""
    c = decodificar_campos(palavra)
    if c["opcode"] == OPCODE_CUSTOM1 and c["funct3"] == FUNCT3_VV:
        nome = NOME_POR_FUNCT6.get(c["funct6"])
        if nome is None:
            raise InstrucaoIlegal(f"funct6 desconhecido: {c['funct6']:06b}")
        if c["vm"] != 1:
            raise InstrucaoIlegal("máscara (vm = 0) fora do escopo")
        if nome == "vncvt.t.t" and c["vs1"] != VS1_VNCVT:
            raise InstrucaoIlegal("sub-opcode (vs1) inválido em vncvt.t.t")
        return nome, c

    return _identificar_padrao(palavra, c)


import re

# --- Montador ---------------------------------------------------------------
_ABI = {"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
        "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9}
_ABI.update({f"a{i}": 10 + i for i in range(8)})        # a0..a7  = x10..x17
_ABI.update({f"s{i}": 16 + i for i in range(2, 12)})    # s2..s11 = x18..x27
_ABI.update({f"t{i}": 25 + i for i in range(3, 7)})     # t3..t6  = x28..x31


def _xreg(tok: str) -> int:
    t = tok.strip().lower()
    if t in _ABI:
        return _ABI[t]
    m = re.fullmatch(r"x(\d+)", t)
    if m and int(m.group(1)) < 32:
        return int(m.group(1))
    raise ValueError(f"registrador escalar inválido: {tok!r}")


def _vreg(tok: str) -> int:
    m = re.fullmatch(r"v(\d+)", tok.strip().lower())
    if m and int(m.group(1)) < 32:
        return int(m.group(1))
    raise ValueError(f"registrador vetorial inválido: {tok!r}")


def _mem(tok: str) -> int:
    """'(a1)' ou '0(a1)' -> número do registrador-base."""
    m = re.fullmatch(r"0?\((\w+)\)", tok.strip())
    if not m:
        raise ValueError(f"operando de memória inválido: {tok!r} (use (reg))")
    return _xreg(m.group(1))


def _imm(tok: str) -> int:
    try:
        return int(tok.strip(), 0)
    except ValueError:
        raise ValueError(f"imediato inválido: {tok!r}") from None


def _zimm(sew: str, lmul: str, vta: str, vma: str) -> int:
    """e8/e16/e32, m1, ta/tu, ma/mu  ->  vtype (vma<<7 | vta<<6 | vsew<<3 | vlmul)."""
    sew, lmul, vta, vma = (s.strip().lower() for s in (sew, lmul, vta, vma))
    if sew not in ("e8", "e16", "e32"):
        raise ValueError(f"SEW fora do escopo: {sew}")
    if lmul != "m1":
        raise ValueError(f"LMUL fora do escopo: {lmul} (projeto usa m1)")
    if vta not in ("ta", "tu") or vma not in ("ma", "mu"):
        raise ValueError("use ta/tu e ma/mu")
    return ((vma == "ma") << 7) | ((vta == "ta") << 6) | ({"e8": 0, "e16": 1, "e32": 2}[sew] << 3)


def _expandir_pseudo(mn: str, ops: list):
    """Pseudo-instruções (todas viram exatamente 1 instrução real)."""
    if mn == "nop":
        return "addi", ["x0", "x0", "0"]
    if mn == "li":
        return "addi", [ops[0], "x0", ops[1]]           # só imediatos de 12 bits
    if mn == "mv":
        return "addi", [ops[0], ops[1], "0"]
    if mn == "bnez":
        return "bne", [ops[0], "x0", ops[1]]
    return mn, ops


def _montar_uma(mn: str, ops: list, pc: int, rotulos: dict) -> int:
    def exige(k):
        if len(ops) != k:
            raise ValueError(f"{mn} espera {k} operandos, recebeu {len(ops)}")

    if mn in FUNCT6_VT:                                  # Zvtakum
        if mn == "vncvt.t.t":
            exige(2)
            return codificar(mn, _vreg(ops[0]), _vreg(ops[1]))
        exige(3)                                         # vd, vs2, vs1
        return codificar(mn, _vreg(ops[0]), _vreg(ops[1]), _vreg(ops[2]))
    if mn == "vsetvli":                                  # rd, rs1, eX, m1, ta, ma
        exige(6)
        return codificar(mn, _xreg(ops[0]), _xreg(ops[1]), _zimm(*ops[2:]))
    if re.fullmatch(r"v[ls]e(8|16|32)\.v", mn):          # vd|vs3, (rs1)
        exige(2)
        return codificar(mn, _vreg(ops[0]), _mem(ops[1]))
    if mn == "addi":
        exige(3)
        return codificar(mn, _xreg(ops[0]), _xreg(ops[1]), _imm(ops[2]))
    if mn == "bne":                                      # rs1, rs2, rótulo | deslocamento
        exige(3)
        alvo = ops[2].strip()
        deslocamento = rotulos[alvo] - pc if alvo in rotulos else _imm(alvo)
        return codificar(mn, _xreg(ops[0]), _xreg(ops[1]), deslocamento)
    raise ValueError(f"instrução desconhecida: {mn}")


def montar(linhas: list) -> list:
    """Texto assembly -> lista de palavras de 32 bits (duas passadas)."""
    # Passada 1: limpa, registra rótulos e expande pseudo-instruções
    itens, rotulos = [], {}
    for num, bruta in enumerate(linhas, 1):
        texto = bruta.split("#")[0].strip()
        while ":" in texto:                              # rótulo(s) no início da linha
            rot, texto = texto.split(":", 1)
            rot = rot.strip()
            if not re.fullmatch(r"[A-Za-z_]\w*", rot):
                raise ValueError(f"linha {num}: rótulo inválido: {rot!r}")
            if rot in rotulos:
                raise ValueError(f"linha {num}: rótulo repetido: {rot}")
            rotulos[rot] = 4 * len(itens)                # endereço em bytes
            texto = texto.strip()
        if not texto:
            continue
        partes = texto.split(None, 1)
        mn = partes[0].lower()
        ops = [o.strip() for o in partes[1].split(",")] if len(partes) > 1 else []
        try:
            mn, ops = _expandir_pseudo(mn, ops)
        except IndexError:
            raise ValueError(f"linha {num}: operandos insuficientes em {mn}") from None
        itens.append((num, mn, ops))

    # Passada 2: codifica
    palavras = []
    for idx, (num, mn, ops) in enumerate(itens):
        try:
            palavras.append(_montar_uma(mn, ops, 4 * idx, rotulos))
        except ValueError as e:
            raise ValueError(f"linha {num}: {e}") from None
    return palavras