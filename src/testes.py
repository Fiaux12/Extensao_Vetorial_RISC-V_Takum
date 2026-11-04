from takum import float_para_takum, takum_para_float, takum_para_binario
from calculos import takum_alargar, takum_estreitar, takum_dot, takum_add, takum_sub, takum_mul

# --- Testes de Calculo ------------------------------
# --- add ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_add(a, b, n) #3.75

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))

# --- sub ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_sub(a, b, n) #-0.75

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))


# --- mul ---
n = 16
a = float_para_takum(1.5, n)
b = float_para_takum(2.25, n)
r = takum_mul(a, b, n) # 3.375

print("a =", takum_para_binario(a, n))
print("b =", takum_para_binario(b, n))
print("r =", takum_para_binario(r, n))
print("valor:", takum_para_float(r, n))

# --- alargar: T8 -> T32 (deve ser exato) ---
a8 = float_para_takum(1.5, 8)
a32 = takum_alargar(a8, 8, 32)
print("T8 :", takum_para_binario(a8, 8), takum_para_float(a8, 8))
print("T32:", takum_para_binario(a32, 32), takum_para_float(a32, 32))
print("exato:", takum_para_float(a8, 8) == takum_para_float(a32, 32))

# --- estreitar: T32 -> T8 (arredonda) ---
x32 = float_para_takum(3.14159, 32)
x8 = takum_estreitar(x32, 32, 8)
print("T32:", takum_para_float(x32, 32))
print("T8 :", takum_para_binario(x8, 8), takum_para_float(x8, 8))

# --- dot: acc + a0*b0 + a1*b1, elementos T16, acumulador T32 ---
n = 16
A = [float_para_takum(v, n) for v in (1.5, 2.0)]
B = [float_para_takum(v, n) for v in (2.0, 3.0)]
acc = float_para_takum(1.0, 32) #10.0

r = takum_dot(acc, A, B, n)
print("dot:", takum_para_binario(r, 32), takum_para_float(r, 32))


# --- Testes de Calculo ------------------------------