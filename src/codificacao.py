"""
codificacao.py
Palavra de 32 bits <-> campos da instrução (montador e decodificador de controle).

Formato OP-V do RVV, usado pela Zvtakum no espaço custom-1:
 31:26 funct6 | 25 vm | 24:20 vs2 | 19:15 vs1 | 14:12 funct3 | 11:7 vd | 6:0 opcode
"""

# --- Opcodes ----------------------------------------------------------------
OPCODE_CUSTOM1 = 0b0101011      # Zvtakum (proposta)
FUNCT3_VV = 0b001

# Instruções padrão que o simulador também precisa reconhecer
# (conferir na especificação, capítulo 30):
OPCODE_OPV = 0b1010111          # vsetvli (funct3 = 111)
OPCODE_LOAD_FP = 0b0000111      # vle8/16/32.v
OPCODE_STORE_FP = 0b0100111     # vse8/16/32.v
OPCODE_OP_IMM = 0b0010011       # addi
OPCODE_BRANCH = 0b1100011       # bne

# --- funct6 das instruções Zvtakum (propostas; confirmar com o grupo) --------
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

    # TODO: instruções padrão. Devolver o nome e os campos que cada executor
    # espera (ver instrucoes.py):
    #   vsetvli, vle8.v / vle16.v / vle32.v, vse8.v / vse16.v / vse32.v,
    #   addi, bne
    raise NotImplementedError(f"decodificação padrão pendente: 0x{palavra:08x}")


def montar(linhas: list) -> list:
    """Texto assembly -> lista de palavras de 32 bits.
    TODO. Alternativa: montar as instruções padrão com o montador GNU e
    inserir as instruções Zvtakum como .word usando codificar_vt()."""
    raise NotImplementedError