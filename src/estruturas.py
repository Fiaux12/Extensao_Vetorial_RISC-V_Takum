"""
estruturas.py
Estado da máquina simulada: registradores, memória, PC, programa e CSRs vetoriais.

Nada aqui interpreta Takum: registradores e memória guardam apenas bits.
"""
from dataclasses import dataclass, field

# --- Parâmetros do modelo (ajustar conforme decidido pelo grupo) ---------------
XLEN = 64                   # largura dos registradores escalares
VLEN = 128                  # bits por registrador vetorial
NUM_REGS_ESC = 32           # x0..x31
NUM_REGS_VET = 32           # v0..v31
TAM_MEMORIA = 64 * 1024     # bytes

MASCARA_XLEN = (1 << XLEN) - 1


@dataclass
class Maquina:
    # Contador de programa, em BYTES (cada instrução ocupa 4 bytes).
    pc: int = 0

    # Banco de registradores escalares (x0 é sempre 0).
    regs_escalares: list = field(
        default_factory=lambda: [0] * NUM_REGS_ESC)

    # Banco de registradores vetoriais: lista de 32 registradores, cada um
    # com VLEN/8 bytes (little-endian: o elemento 0 fica nos bytes de menor índice).
    regs_vetoriais: list = field(
        default_factory=lambda: [bytearray(VLEN // 8) for _ in range(NUM_REGS_VET)])

    # Memória principal (bytes).
    memoria: bytearray = field(default_factory=lambda: bytearray(TAM_MEMORIA))

    # Memória de instruções: lista de palavras de 32 bits (índice = pc // 4).
    programa: list = field(default_factory=list)

    # CSRs vetoriais (vl e os campos da vtype).
    vl: int = 0
    sew: int = 8            # largura do elemento em bits (8, 16 ou 32)
    lmul: int = 1           # neste projeto, fixo em 1
    vta: bool = False       # False = tail undisturbed (tu), True = agnostic (ta)
    vma: bool = False       # False = mask undisturbed (mu), True = agnostic (ma)
    vill: bool = True       # ilegal até o primeiro vsetvli executar

    # --- Parâmetros derivados ----------------------------------------------
    def vlmax(self) -> int:
        """Número máximo de elementos (lanes) com o SEW atual."""
        return (VLEN // self.sew) * self.lmul

    # --- Registradores escalares -------------------------------------------
    def ler_escalar(self, i: int) -> int:
        return self.regs_escalares[i]

    def escrever_escalar(self, i: int, valor: int) -> None:
        if i != 0:                          # x0 é fixo em zero
            self.regs_escalares[i] = valor & MASCARA_XLEN

    # --- Registradores vetoriais (elementos / lanes) -----------------------
    def ler_elemento(self, reg: int, i: int, sew: int | None = None) -> int:
        """Lê o elemento i (padrão de bits, sem interpretar) do registrador reg."""
        sew = sew or self.sew
        n = sew // 8
        ini = i * n
        if ini + n > len(self.regs_vetoriais[reg]):
            raise IndexError(f"elemento {i} fora do registrador v{reg} (SEW={sew})")
        return int.from_bytes(self.regs_vetoriais[reg][ini:ini + n], "little")

    def escrever_elemento(self, reg: int, i: int, valor: int,
                          sew: int | None = None) -> None:
        sew = sew or self.sew
        n = sew // 8
        ini = i * n
        if ini + n > len(self.regs_vetoriais[reg]):
            raise IndexError(f"elemento {i} fora do registrador v{reg} (SEW={sew})")
        self.regs_vetoriais[reg][ini:ini + n] = (valor & ((1 << sew) - 1)).to_bytes(n, "little")

    # --- Memória -----------------------------------------------------------
    def ler_memoria(self, endereco: int, n_bytes: int) -> bytes:
        if endereco < 0 or endereco + n_bytes > len(self.memoria):
            raise IndexError(f"acesso fora da memória: 0x{endereco:x}")
        return bytes(self.memoria[endereco:endereco + n_bytes])

    def escrever_memoria(self, endereco: int, dados: bytes) -> None:
        if endereco < 0 or endereco + len(dados) > len(self.memoria):
            raise IndexError(f"acesso fora da memória: 0x{endereco:x}")
        self.memoria[endereco:endereco + len(dados)] = dados

    # --- Programa ----------------------------------------------------------
    def carregar_programa(self, palavras: list) -> None:
        self.programa = list(palavras)
        self.pc = 0

    def buscar_instrucao(self) -> int:
        """Etapa BUSCAR: devolve a palavra de 32 bits apontada pelo PC."""
        idx = self.pc // 4
        if self.pc % 4 != 0 or not (0 <= idx < len(self.programa)):
            raise IndexError(f"PC inválido: 0x{self.pc:x}")
        return self.programa[idx]

    def fim_do_programa(self) -> bool:
        return self.pc // 4 >= len(self.programa)
