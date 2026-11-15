from takum import float_para_takum, takum_para_float, takum_para_binario
from calculos import takum_alargar, takum_estreitar, takum_dot, takum_add, takum_sub, takum_mul
from estruturas import Maquina, TAM_MEMORIA
from instrucoes import exec_vtadd, exec_vtsub, exec_vtmul, exec_vsetvli, _exec_vle, _exec_vse, exec_addi, exec_bne, exec_vncvt, exec_vtdot8, exec_vtdot16
from codificacao import InstrucaoIlegal, montar
from main import executar

# ==================================================================================
# Testes de Calculo
# ==================================================================================

# --- add ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_add(a, b, n) #3.75

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))
print('\n')

# --- sub ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_sub(a, b, n) #-0.75

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))
print('\n')

# --- mul ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_mul(a, b, n) # 3.375

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))
print('\n')

# --- alargar: T8 -> T32 (deve ser exato) ---
a8 = float_para_takum(1.5, 8)
a32 = takum_alargar(a8, 8, 32)
print("T8 :", takum_para_binario(a8, 8), takum_para_float(a8, 8))
print("T32:", takum_para_binario(a32, 32), takum_para_float(a32, 32))
print("exato:", takum_para_float(a8, 8) == takum_para_float(a32, 32))
print('\n')

# --- estreitar: T32 -> T8 (arredonda) ---
x32 = float_para_takum(3.14159, 32)
x8 = takum_estreitar(x32, 32, 8)
print("T32:", takum_para_float(x32, 32))
print("T8 :", takum_para_binario(x8, 8), takum_para_float(x8, 8))
print('\n')

# --- dot: acc + a0*b0 + a1*b1, elementos T16, acumulador T32 ---
n = 16
A = [float_para_takum(v, n) for v in (1.5, 2.0)]
B = [float_para_takum(v, n) for v in (2.0, 3.0)]
acc = float_para_takum(1.0, 32) #10.0

r = takum_dot(acc, A, B, n)
print("dot:", takum_para_binario(r, 32), takum_para_float(r, 32))

# ==================================================================================
# Testes de Estrutura - Banco de registradores
# ==================================================================================
m1 = Maquina()

# --- Registradores escalares ---
m1.escrever_escalar(5, 123)
print("x5 =", m1.ler_escalar(5))                      # 123

m1.escrever_escalar(0, 999)                           # x0 é fixo em zero
print("x0 =", m1.ler_escalar(0))                      # 0

m1.escrever_escalar(6, -1)                            # cabe em XLEN = 64 bits
print("x6 =", hex(m1.ler_escalar(6)))                 # 0xffffffffffffffff

# --- Registradores vetoriais: escrita por elementos (SEW = 8) ---
for i, v in enumerate([0x11, 0x22, 0x33, 0x44]):
    m1.escrever_elemento(1, i, v, sew=8)
print("v1 bytes:", m1.regs_vetoriais[1][:8].hex(" "))        # 11 22 33 44 00 ...
print("v1[2] (SEW=8) =", hex(m1.ler_elemento(1, 2, sew=8)))  # 0x33

# --- Mesmos bits, lidos com outro SEW (little-endian) ---
print("v1[0] (SEW=16) =", hex(m1.ler_elemento(1, 0, sew=16)))  # 0x2211
print("v1[0] (SEW=32) =", hex(m1.ler_elemento(1, 0, sew=32)))  # 0x44332211

# --- Valor maior que o SEW é truncado (máscara) ---
m1.escrever_elemento(2, 0, 0x1FF, sew=8)
print("v2[0] =", hex(m1.ler_elemento(2, 0, sew=8)))          # 0xff

# --- VLMAX conforme o SEW ---
for sew in (8, 16, 32):
    m1.sew = sew
    print(f"SEW={sew}: VLMAX = {m1.vlmax()}")                 # 16, 8, 4

# --- Acesso fora do registrador ---
try:
    m1.ler_elemento(1, 99, sew=32)
except IndexError as e:
    print("erro esperado:", e)

# ==================================================================================
# Testes de Estrutura - Memoria e PC
# ==================================================================================

m2 = Maquina()

# --- Memória: escrita e leitura de bytes ---
m2.escrever_memoria(0x100, bytes([0x11, 0x22, 0x33, 0x44]))
print("bytes:", m2.ler_memoria(0x100, 4).hex(" "))               # 11 22 33 44
print('\n')

# --- Mesmos bytes lidos como inteiros (little-endian) ---
print("16 bits:", hex(int.from_bytes(m2.ler_memoria(0x100, 2), "little")))  # 0x2211
print("32 bits:", hex(int.from_bytes(m2.ler_memoria(0x100, 4), "little")))  # 0x44332211
print('\n')

# --- Guardar um Takum T16 na memória e recuperar ---
valor = 0x5A3C
m2.escrever_memoria(0x200, valor.to_bytes(2, "little"))
lido = int.from_bytes(m2.ler_memoria(0x200, 2), "little")
print("T16 ida e volta:", hex(lido), lido == valor)            # True
print('\n')

# --- Memória ---
print(m2.ler_memoria(0x100, 4).hex(" ")) 
print(m2.ler_memoria(0x200, 4).hex(" ")) 
print(m2.ler_memoria(0x300, 4).hex(" ")) 
print('\n')

# --- Acesso fora da memória ---
for end in (TAM_MEMORIA - 2, -1):
    try:
        m2.ler_memoria(end, 4)
    except IndexError as e:
        print("erro e_exec_vt_binariasperado:", e)
print('\n')

# --- PC: carregar programa e percorrer ---
m2.carregar_programa([0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC])
print("\nPC inicial:", m2.pc)                                    # 0
while not m2.fim_do_programa():
    print(f"PC={m2.pc}  instrução=0x{m2.buscar_instrucao():08X}")
    m2.pc += 4                                                   # avanço normal (+4)
print("PC final:", m2.pc, "| fim?", m2.fim_do_programa())          # 12, True
print('\n')

# --- Desvio: PC += imediato (como o bne) ---
m2.pc += 8                                                       # salta 2 instruções
print("após desvio de 2 instruções, PC =", m2.pc)                # 12

m2.pc += -4                                                      # desvio para trás (laço)
print("desvio para trás de 1 n=instrução, PC =", m2.pc)                           # 0
print('\n')

# --- PC inválido ---
for pc_ruim in (2, 16, -4):                                     # desalinhado, além do fim, negativo
    m2.pc = pc_ruim
    try:
        m2.buscar_instrucao()
    except IndexError as e:
        print("erro esperado:", e)

# ==================================================================================
# Testes de Instruções - add, sub, mul
# ==================================================================================

m3 = Maquina()
m3.vill, m3.sew, m3.vl = False, 16, 3
for i, (x, y) in enumerate([(1.5, 2.25), (4.0, 0.5), (-2.0, 1.0)]):
    m3.escrever_elemento(2, i, float_para_takum(x, 16))   # vs2
    m3.escrever_elemento(1, i, float_para_takum(y, 16))   # vs1

for i in range(m3.vl):
    valor = m3.ler_elemento(1, i)
    print(f"vs1[{i}] = {takum_para_float(valor, 16)}")

for i in range(m3.vl):
    valor = m3.ler_elemento(2, i)
    print(f"vs2[{i}] =  {takum_para_float(valor, 16)}")

# --- Add -------------------------------------
exec_vtadd(m3, {"vd": 3, "vs2": 2, "vs1": 1})
print([takum_para_float(m3.ler_elemento(3, i), 16) for i in range(4)])
# [3.75, 4.5, -1.0, 0.0]  (a lane 3 é cauda e fica 0)
print('\n')

# --- Sub -------------------------------------
exec_vtsub(m3, {"vd": 3, "vs2": 2, "vs1": 1})
print([takum_para_float(m3.ler_elemento(3, i), 16) for i in range(4)])
# [-75, 3.5, -3.0, 0.0] 
print('\n')

# --- Mul -------------------------------------
exec_vtmul(m3, {"vd": 3, "vs2": 2, "vs1": 1})
print([takum_para_float(m3.ler_elemento(3, i), 16) for i in range(4)])
# [3.37, 2, -2, 0.0] 
print('\n')

# ==================================================================================
# Testes de Instruções - vsetvli, vle / vse, addi, bne, laço: addi + addi + bne
# ==================================================================================
# zimm = vma<<7 | vta<<6 | vsew<<3 | vlmul   (vsew: 0=8, 1=16, 2=32)
E16_M1_TA_MA = (1 << 7) | (1 << 6) | (1 << 3) | 0      # = 200
E32_M1       = (2 << 3)
E64_M1       = (3 << 3)                                 # fora do escopo

# ---------------- vsetvli ----------------
m4 = Maquina()
m4.escrever_escalar(5, 10)                               # t0 = AVL = 10
exec_vsetvli(m4, {"rd": 6, "rs1": 5, "zimm": E16_M1_TA_MA})
print("SEW =", m4.sew, "| vlmax =", m4.vlmax(), "| vl =", m4.vl, "| x6 =", m4.ler_escalar(6))
print('\n')

# ---------------- vle / vse ----------------

# ---------------- addi ----------------
m5 = Maquina()
m5.escrever_escalar(5, 10)
exec_addi(m5, {"rd": 6, "rs1": 5, "imm": -3})
print("addi x6 = x5 - 3 =", m5.ler_escalar(6))           # 7

# ---------------- bne ----------------
m6 = Maquina()
m6.pc = 8
m6.escrever_escalar(1, 1)
m6.escrever_escalar(2, 2)
r = exec_bne(m6, {"rs1": 1, "rs2": 2, "imm": -8})
print("diferentes: desviou =", r, "| pc =", m6.pc)       # True | 0
print('\n')

m6.pc = 8
m6.escrever_escalar(2, 1)
r = exec_bne(m6, {"rs1": 1, "rs2": 2, "imm": -8})
print("iguais: desviou =", r, "| pc =", m6.pc)           # False | 8
print('\n')

# ---------------- laço: addi + addi + bne ----------------
m7 = Maquina()
m7.escrever_escalar(7, 3)                                # contador = 3
prog = [
    (exec_addi, {"rd": 6, "rs1": 6, "imm": 1}),         # 0: x6 += 1
    (exec_addi, {"rd": 7, "rs1": 7, "imm": -1}),        # 4: x7 -= 1
    (exec_bne,  {"rs1": 7, "rs2": 0, "imm": -8}),       # 8: se x7 != 0, volta ao pc=0
]
print("x7 =", m7.ler_escalar(7))  


m7.carregar_programa([0] * len(prog))                    # só para o PC saber o tamanho
while not m7.fim_do_programa():
    f, c = prog[m7.pc // 4]
    if not f(m7, c):
        m7.pc += 4
print("laço: x6 =", m7.ler_escalar(6), "| x7 =", m7.ler_escalar(7))   # 3 | 0

# ==================================================================================
# Testes de Instruções - vncvt e dot
# ==================================================================================
# ---------------- vncvt ----------------
m8 = Maquina()
m8.vill, m8.sew, m8.vl = False, 16, 4                    # destino T16, 4 lanes
for i, v in enumerate([3.14159, -2.5, 100.0, 0.001]):
    m8.escrever_elemento(2, i, float_para_takum(v, 32), sew=32)   # fonte T32 em v2
exec_vncvt(m8, {"vd": 4, "vs2": 2, "vs1": 0b10100})
print([takum_para_float(m8.ler_elemento(4, i, 16), 16) for i in range(4)])
# ~[3.14, -2.5, 100.0, 0.001], com o arredondamento do T16

# ---------------- dot ----------------
def preparar(sew=32, vl=2):
    m = Maquina()
    m.vill, m.sew, m.vl = False, sew, vl
    return m

def mostrar(m, nome, reg, n, k):
    for lane in range(m.vl):
        elems = [takum_para_float(m.ler_elemento(reg, lane * k + j, sew=n), n) for j in range(k)]
        print(f"{nome} lane {lane}: {elems}")

m = preparar(vl=2)
A = [1, 2, 3, 0.5,   -1, 1, 2, 2]              # vs2 = v2 (8 elementos T8)
B = [1, 1, 2, 4,      1, 1, 0.5, 0.25]         # vs1 = v1
for i in range(8):
    m.escrever_elemento(2, i, float_para_takum(A[i], 8), sew=8)
    m.escrever_elemento(1, i, float_para_takum(B[i], 8), sew=8)
m.escrever_elemento(3, 0, float_para_takum(10.0, 32), sew=32)    # acumulador inicial em vd[0]
m.escrever_elemento(3, 1, float_para_takum(5.0, 32), sew=32)     # vd[1]: não deve ser alterado

mostrar(m, "vs2", 2, 8, 4)
mostrar(m, "vs1", 1, 8, 4)

exec_vtdot8(m, {"vd": 3, "vs2": 2, "vs1": 1})

r = takum_para_float(m.ler_elemento(3, 0, sew=32), 32)
print(f"vtdot8: vd[0] = {r:.4f} (esperado 22.5 = 10 + 11 + 1.5)")
print("vd[1] intacto:", takum_para_float(m.ler_elemento(3, 1, sew=32), 32), "(esperado 5.0)")

# ---------------- vtdot16: 2 lanes x 2 elementos T16 ----------------
m = preparar(vl=2)
A = [1.5, 2.0, -1.0, 4.0]
B = [2.0, 3.0,  0.5, 0.25]
for i in range(4):
    m.escrever_elemento(2, i, float_para_takum(A[i], 16), sew=16)
    m.escrever_elemento(1, i, float_para_takum(B[i], 16), sew=16)
m.escrever_elemento(3, 0, float_para_takum(0.0, 32), sew=32)

exec_vtdot16(m, {"vd": 3, "vs2": 2, "vs1": 1})
r = takum_para_float(m.ler_elemento(3, 0, sew=32), 32)
print(f"vtdot16: vd[0] = {r:.4f} (esperado 9.5 = 1 + 3 + 6 - 0.5 + 1)")


# ==================================================================================
# Testes Do Funcionamento Geral
# ==================================================================================

# ---------------- add/sub/mult ----------------
def mostrar_memoria(m, titulo, ini, qtd, n):
    print(f"\n{titulo}")
    print("  endereço | binário          | hex    | valor")
    for i in range(qtd):
        end = ini + i * (n // 8)
        bits = int.from_bytes(m.ler_memoria(end, n // 8), "little")
        print(f"  0x{end:04X}   | {bits:0{n}b} | 0x{bits:0{n // 4}X} | {takum_para_float(bits, n):.6g}")


def mostrar_escalares(m):
    print("\nBanco de registradores escalares (só os diferentes de zero)")
    for i, v in enumerate(m.regs_escalares):
        if v != 0:
            print(f"  x{i:<2} = {v} (0x{v:X})")


def mostrar_vetorial(m, reg, n):
    print(f"\nv{reg}  (SEW = {n}, vl = {m.vl}, VLMAX = {len(m.regs_vetoriais[reg]) * 8 // n})")
    print("  bytes:", m.regs_vetoriais[reg].hex(" "))
    print("  lane | binário          | valor        | obs")
    for i in range(len(m.regs_vetoriais[reg]) * 8 // n):
        bits = m.ler_elemento(reg, i, sew=n)
        obs = "" if i < m.vl else "cauda (>= vl)"
        print(f"  {i:<4} | {bits:0{n}b} | {takum_para_float(bits, n):<10.6g} | {obs}")

END_X, END_Y, END_Z = 0x100, 0x200, 0x300
N = 16                                 
QTD = 4
m = Maquina()

m.carregar_programa(montar([
    f"li a0, {END_X}",                 # Carregar Imediato
    f"li a1, {END_Y}",
    f"li a2, {END_Z}",
    f"li t1, {QTD}",
    "vsetvli t0, t1, e16, m1, ta, ma", #configura o processador vetorial antes de realizar operações com vetores
    "vle16.v v1, (a0)",                # Operação de carga vetorial de elementos de 16 bits contínuos da memória para um registrador vetorial.
    "vle16.v v2, (a1)",
    "vtadd.vv v3, v1, v2",             # add/sub/mult
    "vse16.v v3, (a2)",                # Salvar) um vetor de elementos de 16 bits da memória de registradores vetoriais para a memória RAM
]))

X = [1.5, 2.0, -3.0, 0.5]
Y = [2.25, 4.0, 1.0, 0.5]
for i in range(QTD):
    m.escrever_memoria(END_X + 2 * i, float_para_takum(X[i], N).to_bytes(2, "little"))
    m.escrever_memoria(END_Y + 2 * i, float_para_takum(Y[i], N).to_bytes(2, "little"))
 
print("=== ANTES ===")
mostrar_memoria(m, "Memória: vetor X", END_X, QTD, N)
mostrar_memoria(m, "Memória: vetor Y", END_Y, QTD, N)
mostrar_memoria(m, "Memória: resultado Z (ainda zerado)", END_Z, QTD, N)
 
executar(m)
 
print("\n=== DEPOIS ===")
mostrar_memoria(m, "Memória: vetor X", END_X, QTD, N)
mostrar_memoria(m, "Memória: vetor Y", END_Y, QTD, N)
mostrar_memoria(m, "Memória: resultado Z = X + Y", END_Z, QTD, N)
mostrar_escalares(m)
for r in (1, 2, 3):
    mostrar_vetorial(m, r, N)


# ---------------- vncvt  ----------------
END_X, END_Z = 0x100, 0x200
QTD = 4


def mostrar_memoria(m, titulo, ini, qtd, n):
    print(f"\n{titulo}")
    print("  endereço | binário                          | hex        | valor")
    for i in range(qtd):
        end = ini + i * (n // 8)
        bits = int.from_bytes(m.ler_memoria(end, n // 8), "little")
        print(f"  0x{end:04X}   | {bits:0{n}b} | 0x{bits:0{n // 4}X} | {takum_para_float(bits, n):.8g}")


def mostrar_vetorial(m, reg, n, ativas):
    total = len(m.regs_vetoriais[reg]) * 8 // n
    print(f"\nv{reg}  (lido como T{n}, {ativas} elementos ativos de {total})")
    print("  bytes:", m.regs_vetoriais[reg].hex(" "))
    for i in range(total):
        bits = m.ler_elemento(reg, i, sew=n)
        print(f"  lane {i:<2} | {takum_para_float(bits, n):<12.8g} | {'' if i < ativas else 'cauda'}")


m = Maquina()
m.carregar_programa(montar([
    f"li a0, {END_X}", f"li a2, {END_Z}",
    f"li t1, {QTD}",
    "vsetvli t0, t1, e32, m1, ta, ma",    # SEW = 32 para carregar os T32
    "vle32.v v2, (a0)",                   # fonte: 4 elementos T32
    "vsetvli t0, t1, e16, m1, ta, ma",    # SEW = 16 = largura do destino
    "vncvt.t.t v4, v2",                   # T32 -> T16
    "vse16.v v4, (a2)",                   # 4 elementos T16 -> memória
]))

X = [3.14159, -2.5, 100.0, 0.001]
for i in range(QTD):
    m.escrever_memoria(END_X + 4 * i, float_para_takum(X[i], 32).to_bytes(4, "little"))

print("=== ANTES ===")
mostrar_memoria(m, "Memória: fonte (T32)", END_X, QTD, 32)
mostrar_memoria(m, "Memória: destino (T16, ainda zerado)", END_Z, QTD, 16)

executar(m)

print("\n=== DEPOIS ===")
mostrar_memoria(m, "Memória: destino (T16)", END_Z, QTD, 16)
mostrar_vetorial(m, 2, 32, QTD)        # fonte (v2 ocupa 4 lanes de 32 bits)
mostrar_vetorial(m, 4, 16, QTD)        # destino (v4, 4 lanes ativas de 16 bits)

print("\nErro de arredondamento do estreitamento:")
for i in range(QTD):
    orig = takum_para_float(int.from_bytes(m.ler_memoria(END_X + 4 * i, 4), "little"), 32)
    conv = takum_para_float(int.from_bytes(m.ler_memoria(END_Z + 2 * i, 2), "little"), 16)
    print(f"  T32 {orig:<12.8g} -> T16 {conv:<12.8g}  erro relativo = {abs(conv - orig) / abs(orig):.2e}")

# ---------------- produto escalar vetorial  ----------------


END_X, END_Y, END_ACC, END_Z = 0x100, 0x200, 0x300, 0x400


def mostrar_memoria(m, titulo, ini, qtd, n):
    print(f"\n{titulo}")
    print("  endereço | binário                          | hex        | valor")
    for i in range(qtd):
        end = ini + i * (n // 8)
        bits = int.from_bytes(m.ler_memoria(end, n // 8), "little")
        print(f"  0x{end:04X}   | {bits:0{n}b} | 0x{bits:0{n // 4}X} | {takum_para_float(bits, n):.6g}")


def mostrar_vetorial(m, reg, n, ativas):
    """ativas = número de elementos de n bits dentro de vl (o resto é cauda)."""
    total = len(m.regs_vetoriais[reg]) * 8 // n
    print(f"\nv{reg}  (lido como T{n}, {ativas} elementos ativos de {total})")
    print("  bytes:", m.regs_vetoriais[reg].hex(" "))
    for i in range(total):
        bits = m.ler_elemento(reg, i, sew=n)
        print(f"  lane {i:<2} | {takum_para_float(bits, n):<10.6g} | {'' if i < ativas else 'cauda'}")


m = Maquina()
m.carregar_programa(montar([
    f"li a0, {END_X}",
    f"li a1, {END_Y}", 
    f"li a2, {END_ACC}", 
    f"li a3, {END_Z}",
    "li t1, 2",                           # 2 lanes de 32 bits = 8 elementos T8
    "vsetvli t0, t1, e32, m1, ta, ma",
    "vle32.v v1, (a0)",                   # 8 elementos T8 (X)
    "vle32.v v2, (a1)",                   # 8 elementos T8 (Y)
    "vle32.v v3, (a2)",                   # acumulador inicial em v3[0]
    "vtdot8.vv v3, v2, v1",
    "li t1, 1",
    "vsetvli t0, t1, e32, m1, ta, ma",    # vl = 1 para gravar só o escalar
    "vse32.v v3, (a3)",                   # 1 elemento T32 -> memória
]))

X = [1.5, 2.0, -3.0, 0.5,  1.0, 2.0, 3.0, 4.0]     # lane 0 | lane 1
Y = [2.25, 4.0, 1.0, 0.5,  1.0, 0.5, 0.5, 0.25]
for i in range(8):                                  # T8 = 1 byte por elemento
    m.escrever_memoria(END_X + i, float_para_takum(X[i], 8).to_bytes(1, "little"))
    m.escrever_memoria(END_Y + i, float_para_takum(Y[i], 8).to_bytes(1, "little"))
m.escrever_memoria(END_ACC, float_para_takum(10.0, 32).to_bytes(4, "little"))   # acumulador T32

print("=== ANTES ===")
mostrar_memoria(m, "Memória: X (T8)", END_X, 8, 8)
mostrar_memoria(m, "Memória: Y (T8)", END_Y, 8, 8)
mostrar_memoria(m, "Memória: acumulador inicial (T32)", END_ACC, 1, 32)
mostrar_memoria(m, "Memória: resultado (T32, ainda zerado)", END_Z, 1, 32)

executar(m)

print("\n=== DEPOIS ===")
mostrar_memoria(m, "Memória: resultado = acc + X·Y (T32)", END_Z, 1, 32)
mostrar_vetorial(m, 1, 8, 8)       # X em v1, lido como T8
mostrar_vetorial(m, 2, 8, 8)       # Y em v2
mostrar_vetorial(m, 3, 32, 1)      # v3: só a lane 0 é o resultado
print("\nesperado (valores exatos): 10 + 8.625 + 4.5 = 23.125 (T8 introduz erro nas entradas)")