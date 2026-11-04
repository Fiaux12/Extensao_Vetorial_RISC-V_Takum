from takum import float_para_takum, takum_para_float, takum_para_binario
from calculos import takum_alargar, takum_estreitar, takum_dot, takum_add, takum_sub, takum_mul
from estruturas import Maquina, TAM_MEMORIA

# ------------------------------ Testes de Calculo ------------------------------
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


# ------------------------------ Testes de Estrutura - Banco de registradores ------------------------------
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


# ------------------------------ Testes de Estrutura - Memoria e PC ------------------------------

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
        print("erro esperado:", e)
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