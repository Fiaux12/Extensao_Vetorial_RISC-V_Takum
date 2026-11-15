"""
Testes automáticos (unittest) do simulador Zvtakum.

Reproduz, com asserts, os testes que antes eram só prints em testes.py.
Executar:  python -m unittest testes_automaticos -v
(também funciona com:  pytest testes_automaticos.py)
"""
import math
import unittest

from takum import float_para_takum, takum_para_float, nar, eh_nar
from calculos import (takum_alargar, takum_estreitar, takum_dot,
                      takum_add, takum_sub, takum_mul)
from estruturas import Maquina, TAM_MEMORIA
from instrucoes import (exec_vtadd, exec_vtsub, exec_vtmul, exec_vsetvli,
                        exec_addi, exec_bne, exec_vncvt,
                        exec_vtdot8, exec_vtdot16)
from codificacao import InstrucaoIlegal, montar, codificar, identificar
from main import executar


def T(v, n):
    return float_para_takum(v, n)


def F(bits, n):
    return takum_para_float(bits, n)


class TestCase(unittest.TestCase):
    def assertProximo(self, obtido, esperado, rel=1e-3, abs_=1e-9):
        self.assertTrue(math.isclose(obtido, esperado, rel_tol=rel, abs_tol=abs_),
                        f"obtido {obtido}, esperado {esperado} (rel={rel})")


# =============================================================================
# Cálculo (ULA)
# =============================================================================
class TestCalculo(TestCase):
    n = 16

    def test_add(self):
        r = takum_add(T(1.5, self.n), T(2.25, self.n), self.n)
        self.assertProximo(F(r, self.n), 3.75)

    def test_sub(self):
        r = takum_sub(T(1.5, self.n), T(2.25, self.n), self.n)
        self.assertProximo(F(r, self.n), -0.75)

    def test_mul(self):
        r = takum_mul(T(1.5, self.n), T(2.25, self.n), self.n)
        self.assertProximo(F(r, self.n), 3.375)

    def test_casos_especiais(self):
        n = self.n
        um = T(1.0, n)
        self.assertTrue(eh_nar(takum_add(nar(n), um, n), n))
        self.assertTrue(eh_nar(takum_mul(um, nar(n), n), n))
        self.assertEqual(takum_add(0, um, n), um)           # zero é neutro na soma
        self.assertEqual(takum_mul(0, um, n), 0)            # zero absorve na mult.
        self.assertEqual(takum_sub(um, um, n), 0)           # a - a = 0

    def test_alargar_t8_t32_exato(self):
        a8 = T(1.5, 8)
        a32 = takum_alargar(a8, 8, 32)
        self.assertEqual(F(a8, 8), F(a32, 32))

    def test_estreitar_t32_t8(self):
        x32 = T(3.14159, 32)
        x8 = takum_estreitar(x32, 32, 8)
        self.assertProximo(F(x8, 8), 3.14159, rel=0.1)

    def test_dot_t16_acumulador_t32(self):
        n = 16
        A = [T(v, n) for v in (1.5, 2.0)]
        B = [T(v, n) for v in (2.0, 3.0)]
        r = takum_dot(T(1.0, 32), A, B, n)                  # 1 + 3 + 6
        self.assertProximo(F(r, 32), 10.0)


# =============================================================================
# Estruturas: registradores, memória e PC
# =============================================================================
class TestRegistradores(TestCase):
    def setUp(self):
        self.m = Maquina()

    def test_escalares(self):
        self.m.escrever_escalar(5, 123)
        self.assertEqual(self.m.ler_escalar(5), 123)

    def test_x0_fixo_em_zero(self):
        self.m.escrever_escalar(0, 999)
        self.assertEqual(self.m.ler_escalar(0), 0)

    def test_escalar_truncado_em_xlen(self):
        self.m.escrever_escalar(6, -1)
        self.assertEqual(self.m.ler_escalar(6), 0xFFFFFFFFFFFFFFFF)

    def test_vetorial_little_endian_e_sew(self):
        m = self.m
        for i, v in enumerate([0x11, 0x22, 0x33, 0x44]):
            m.escrever_elemento(1, i, v, sew=8)
        self.assertEqual(bytes(m.regs_vetoriais[1][:4]), bytes([0x11, 0x22, 0x33, 0x44]))
        self.assertEqual(m.ler_elemento(1, 2, sew=8), 0x33)
        self.assertEqual(m.ler_elemento(1, 0, sew=16), 0x2211)
        self.assertEqual(m.ler_elemento(1, 0, sew=32), 0x44332211)

    def test_valor_maior_que_sew_e_truncado(self):
        self.m.escrever_elemento(2, 0, 0x1FF, sew=8)
        self.assertEqual(self.m.ler_elemento(2, 0, sew=8), 0xFF)

    def test_vlmax(self):
        for sew, esperado in ((8, 16), (16, 8), (32, 4)):
            self.m.sew = sew
            self.assertEqual(self.m.vlmax(), esperado)

    def test_elemento_fora_do_registrador(self):
        with self.assertRaises(IndexError):
            self.m.ler_elemento(1, 99, sew=32)


class TestMemoriaPC(TestCase):
    def setUp(self):
        self.m = Maquina()

    def test_bytes_e_inteiros_little_endian(self):
        self.m.escrever_memoria(0x100, bytes([0x11, 0x22, 0x33, 0x44]))
        self.assertEqual(self.m.ler_memoria(0x100, 4), bytes([0x11, 0x22, 0x33, 0x44]))
        self.assertEqual(int.from_bytes(self.m.ler_memoria(0x100, 2), "little"), 0x2211)
        self.assertEqual(int.from_bytes(self.m.ler_memoria(0x100, 4), "little"), 0x44332211)

    def test_t16_ida_e_volta(self):
        valor = 0x5A3C
        self.m.escrever_memoria(0x200, valor.to_bytes(2, "little"))
        self.assertEqual(int.from_bytes(self.m.ler_memoria(0x200, 2), "little"), valor)

    def test_memoria_nao_escrita_e_zero(self):
        self.assertEqual(self.m.ler_memoria(0x300, 4), bytes(4))

    def test_acesso_fora_da_memoria(self):
        for end in (TAM_MEMORIA - 2, -1):
            with self.assertRaises(IndexError):
                self.m.ler_memoria(end, 4)
        with self.assertRaises(IndexError):
            self.m.escrever_memoria(TAM_MEMORIA - 1, bytes(2))

    def test_percorrer_programa(self):
        m = self.m
        prog = [0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC]
        m.carregar_programa(prog)
        self.assertEqual(m.pc, 0)
        lidas = []
        while not m.fim_do_programa():
            lidas.append(m.buscar_instrucao())
            m.pc += 4
        self.assertEqual(lidas, prog)
        self.assertEqual(m.pc, 12)
        self.assertTrue(m.fim_do_programa())

    def test_desvio_do_pc(self):
        self.m.pc = 12
        self.m.pc += -4
        self.assertEqual(self.m.pc, 8)

    def test_pc_invalido(self):
        self.m.carregar_programa([0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC])
        for pc_ruim in (2, 16, -4):         # desalinhado, além do fim, negativo
            self.m.pc = pc_ruim
            with self.assertRaises(IndexError):
                self.m.buscar_instrucao()


# =============================================================================
# Instruções: vtadd, vtsub, vtmul
# =============================================================================
class TestAritmeticaVetorial(TestCase):
    def setUp(self):
        m = self.m = Maquina()
        m.vill, m.sew, m.vl = False, 16, 3
        for i, (x, y) in enumerate([(1.5, 2.25), (4.0, 0.5), (-2.0, 1.0)]):
            m.escrever_elemento(2, i, T(x, 16))     # vs2
            m.escrever_elemento(1, i, T(y, 16))     # vs1
        self.c = {"vd": 3, "vs2": 2, "vs1": 1}

    def lanes(self):
        return [F(self.m.ler_elemento(3, i), 16) for i in range(4)]

    def confere(self, esperado):
        for obtido, esp in zip(self.lanes(), esperado):
            self.assertProximo(obtido, esp, rel=1e-2, abs_=1e-6)

    def test_vtadd(self):
        exec_vtadd(self.m, self.c)
        self.confere([3.75, 4.5, -1.0, 0.0])        # lane 3 é cauda: fica 0

    def test_vtsub(self):                            # vd = vs2 - vs1
        exec_vtsub(self.m, self.c)
        self.confere([-0.75, 3.5, -3.0, 0.0])

    def test_vtmul(self):
        exec_vtmul(self.m, self.c)
        self.confere([3.375, 2.0, -2.0, 0.0])

    def test_cauda_preservada(self):
        self.m.escrever_elemento(3, 3, 0xABCD)
        exec_vtadd(self.m, self.c)
        self.assertEqual(self.m.ler_elemento(3, 3), 0xABCD)

    def test_exige_vsetvli(self):
        self.m.vill = True
        with self.assertRaises(InstrucaoIlegal):
            exec_vtadd(self.m, self.c)


# =============================================================================
# Instruções padrão: vsetvli, addi, bne, laço
# =============================================================================
E16_M1_TA_MA = (1 << 7) | (1 << 6) | (1 << 3) | 0   # = 200
E32_M1 = 2 << 3
E64_M1 = 3 << 3                                      # fora do escopo


class TestInstrucoesPadrao(TestCase):
    def test_vsetvli_e16(self):
        m = Maquina()
        m.escrever_escalar(5, 10)                    # AVL = 10
        exec_vsetvli(m, {"rd": 6, "rs1": 5, "zimm": E16_M1_TA_MA})
        self.assertEqual(m.sew, 16)
        self.assertEqual(m.vlmax(), 8)
        self.assertEqual(m.vl, 8)                    # min(10, 8)
        self.assertEqual(m.ler_escalar(6), 8)
        self.assertFalse(m.vill)
        self.assertTrue(m.vta and m.vma)

    def test_vsetvli_avl_menor_que_vlmax(self):
        m = Maquina()
        m.escrever_escalar(5, 3)
        exec_vsetvli(m, {"rd": 6, "rs1": 5, "zimm": E32_M1})
        self.assertEqual(m.vl, 3)

    def test_vsetvli_rs1_x0_usa_vlmax(self):
        m = Maquina()
        exec_vsetvli(m, {"rd": 6, "rs1": 0, "zimm": E32_M1})
        self.assertEqual(m.vl, 4)

    def test_vsetvli_sew_fora_do_escopo(self):
        m = Maquina()
        m.escrever_escalar(5, 3)
        exec_vsetvli(m, {"rd": 6, "rs1": 5, "zimm": E64_M1})
        self.assertTrue(m.vill)
        self.assertEqual(m.vl, 0)

    def test_addi(self):
        m = Maquina()
        m.escrever_escalar(5, 10)
        exec_addi(m, {"rd": 6, "rs1": 5, "imm": -3})
        self.assertEqual(m.ler_escalar(6), 7)

    def test_bne_diferentes_desvia(self):
        m = Maquina()
        m.pc = 8
        m.escrever_escalar(1, 1)
        m.escrever_escalar(2, 2)
        self.assertTrue(exec_bne(m, {"rs1": 1, "rs2": 2, "imm": -8}))
        self.assertEqual(m.pc, 0)

    def test_bne_iguais_nao_desvia(self):
        m = Maquina()
        m.pc = 8
        m.escrever_escalar(1, 1)
        m.escrever_escalar(2, 1)
        self.assertFalse(exec_bne(m, {"rs1": 1, "rs2": 2, "imm": -8}))
        self.assertEqual(m.pc, 8)

    def test_laco_addi_addi_bne(self):
        m = Maquina()
        m.escrever_escalar(7, 3)
        prog = [
            (exec_addi, {"rd": 6, "rs1": 6, "imm": 1}),
            (exec_addi, {"rd": 7, "rs1": 7, "imm": -1}),
            (exec_bne,  {"rs1": 7, "rs2": 0, "imm": -8}),
        ]
        m.carregar_programa([0] * len(prog))
        while not m.fim_do_programa():
            f, c = prog[m.pc // 4]
            if not f(m, c):
                m.pc += 4
        self.assertEqual(m.ler_escalar(6), 3)
        self.assertEqual(m.ler_escalar(7), 0)


# =============================================================================
# Instruções: vncvt e vtdot
# =============================================================================
class TestVncvtDot(TestCase):
    def test_vncvt_t32_para_t16(self):
        m = Maquina()
        m.vill, m.sew, m.vl = False, 16, 4
        valores = [3.14159, -2.5, 100.0, 0.001]
        for i, v in enumerate(valores):
            m.escrever_elemento(2, i, T(v, 32), sew=32)
        exec_vncvt(m, {"vd": 4, "vs2": 2, "vs1": 0b10100})
        for i, v in enumerate(valores):
            self.assertProximo(F(m.ler_elemento(4, i, 16), 16), v, rel=1e-2)

    def test_vncvt_rejeita_sew32_e_vs2_impar(self):
        m = Maquina()
        m.vill, m.sew, m.vl = False, 32, 1
        with self.assertRaises(InstrucaoIlegal):
            exec_vncvt(m, {"vd": 4, "vs2": 2, "vs1": 0b10100})
        m.sew = 16
        with self.assertRaises(InstrucaoIlegal):
            exec_vncvt(m, {"vd": 4, "vs2": 3, "vs1": 0b10100})

    @staticmethod
    def preparar(vl):
        m = Maquina()
        m.vill, m.sew, m.vl = False, 32, vl
        return m

    def test_vtdot8(self):
        m = self.preparar(2)
        A = [1, 2, 3, 0.5, -1, 1, 2, 2]
        B = [1, 1, 2, 4, 1, 1, 0.5, 0.25]
        for i in range(8):
            m.escrever_elemento(2, i, T(A[i], 8), sew=8)
            m.escrever_elemento(1, i, T(B[i], 8), sew=8)
        m.escrever_elemento(3, 0, T(10.0, 32), sew=32)
        m.escrever_elemento(3, 1, T(5.0, 32), sew=32)
        exec_vtdot8(m, {"vd": 3, "vs2": 2, "vs1": 1})
        # esperado 22.5 com valores exatos; T8 quantiza as entradas, então
        # comparamos com os valores já quantizados (o dot é feito em T32)
        q = lambda v: F(T(v, 8), 8)
        esperado = 10 + sum(q(a) * q(b) for a, b in zip(A, B))
        self.assertProximo(F(m.ler_elemento(3, 0, sew=32), 32), esperado, rel=1e-3)
        self.assertProximo(F(m.ler_elemento(3, 0, sew=32), 32), 22.5, rel=0.05)
        self.assertProximo(F(m.ler_elemento(3, 1, sew=32), 32), 5.0, rel=1e-6)    # intacto

    def test_vtdot16(self):
        m = self.preparar(2)
        A = [1.5, 2.0, -1.0, 4.0]
        B = [2.0, 3.0, 0.5, 0.25]
        for i in range(4):
            m.escrever_elemento(2, i, T(A[i], 16), sew=16)
            m.escrever_elemento(1, i, T(B[i], 16), sew=16)
        m.escrever_elemento(3, 0, T(0.0, 32), sew=32)
        exec_vtdot16(m, {"vd": 3, "vs2": 2, "vs1": 1})
        self.assertProximo(F(m.ler_elemento(3, 0, sew=32), 32), 9.5, rel=1e-2)

    def test_vtdot_exige_sew32(self):
        m = self.preparar(2)
        m.sew = 16
        with self.assertRaises(InstrucaoIlegal):
            exec_vtdot8(m, {"vd": 3, "vs2": 2, "vs1": 1})

    def test_vtdot_vl_zero_nao_altera(self):
        m = self.preparar(0)
        m.escrever_elemento(3, 0, T(7.0, 32), sew=32)
        exec_vtdot8(m, {"vd": 3, "vs2": 2, "vs1": 1})
        self.assertProximo(F(m.ler_elemento(3, 0, sew=32), 32), 7.0, rel=1e-6)


# =============================================================================
# Codificação / montador
# =============================================================================
class TestCodificacao(TestCase):
    def test_vtmul_palavra_conhecida(self):
        self.assertEqual(codificar("vtmul.vv", 1, 2, 3), 0x922190AB)

    def test_ida_e_volta_vt(self):
        for nome in ("vtadd.vv", "vtsub.vv", "vtmul.vv",
                     "vtdot8.vv", "vtdot16.vv", "vtdot32.vv"):
            n, c = identificar(codificar(nome, 1, 2, 3))
            self.assertEqual((n, c["vd"], c["vs2"], c["vs1"]), (nome, 1, 2, 3))

    def test_ida_e_volta_vncvt(self):
        nome, c = identificar(codificar("vncvt.t.t", 4, 2))
        self.assertEqual(nome, "vncvt.t.t")
        self.assertEqual((c["vd"], c["vs2"], c["vs1"]), (4, 2, 0b10100))

    def test_ida_e_volta_padrao(self):
        nome, c = identificar(codificar("addi", 6, 5, -3))
        self.assertEqual((nome, c["rd"], c["rs1"], c["imm"]), ("addi", 6, 5, -3))
        nome, c = identificar(codificar("bne", 1, 2, -8))
        self.assertEqual((nome, c["rs1"], c["rs2"], c["imm"]), ("bne", 1, 2, -8))
        nome, c = identificar(codificar("vle16.v", 1, 10))
        self.assertEqual((nome, c["vd"], c["rs1"]), ("vle16.v", 1, 10))
        nome, c = identificar(codificar("vse32.v", 3, 12))
        self.assertEqual((nome, c["vs3"], c["rs1"]), ("vse32.v", 3, 12))

    def test_palavra_ilegal(self):
        with self.assertRaises(InstrucaoIlegal):
            identificar(0xFFFFFFFF)

    def test_montador_rotulo_e_pseudo(self):
        palavras = montar(["li t0, 3", "laco:", "addi t0, t0, -1", "bnez t0, laco"])
        self.assertEqual(len(palavras), 3)
        nome, c = identificar(palavras[2])
        self.assertEqual((nome, c["imm"]), ("bne", -4))

    def test_montador_erros(self):
        for ruim in (["foo v1, v2"], ["vtadd.vv v1, v2"], ["vsetvli t0, t1, e64, m1, ta, ma"]):
            with self.assertRaises(ValueError):
                montar(ruim)


# =============================================================================
# Funcionamento geral: programas completos no simulador
# =============================================================================
class TestProgramasCompletos(TestCase):
    def test_soma_vetorial_t16(self):
        X_, Y_, Z_, N, QTD = 0x100, 0x200, 0x300, 16, 4
        m = Maquina()
        m.carregar_programa(montar([
            f"li a0, {X_}", f"li a1, {Y_}", f"li a2, {Z_}", f"li t1, {QTD}",
            "vsetvli t0, t1, e16, m1, ta, ma",
            "vle16.v v1, (a0)", "vle16.v v2, (a1)",
            "vtadd.vv v3, v1, v2",
            "vse16.v v3, (a2)",
        ]))
        X = [1.5, 2.0, -3.0, 0.5]
        Y = [2.25, 4.0, 1.0, 0.5]
        for i in range(QTD):
            m.escrever_memoria(X_ + 2 * i, T(X[i], N).to_bytes(2, "little"))
            m.escrever_memoria(Y_ + 2 * i, T(Y[i], N).to_bytes(2, "little"))
        executar(m)
        for i in range(QTD):
            bits = int.from_bytes(m.ler_memoria(Z_ + 2 * i, 2), "little")
            self.assertProximo(F(bits, N), X[i] + Y[i], rel=1e-2)
        self.assertEqual(m.ler_escalar(10), X_)            # a0 intacto
        self.assertEqual(m.ler_escalar(5), QTD)            # t0 = vl

    def test_vncvt_t32_para_t16_em_memoria(self):
        X_, Z_, QTD = 0x100, 0x200, 4
        m = Maquina()
        m.carregar_programa(montar([
            f"li a0, {X_}", f"li a2, {Z_}", f"li t1, {QTD}",
            "vsetvli t0, t1, e32, m1, ta, ma",
            "vle32.v v2, (a0)",
            "vsetvli t0, t1, e16, m1, ta, ma",
            "vncvt.t.t v4, v2",
            "vse16.v v4, (a2)",
        ]))
        X = [3.14159, -2.5, 100.0, 0.001]
        for i in range(QTD):
            m.escrever_memoria(X_ + 4 * i, T(X[i], 32).to_bytes(4, "little"))
        executar(m)
        for i in range(QTD):
            orig = F(int.from_bytes(m.ler_memoria(X_ + 4 * i, 4), "little"), 32)
            conv = F(int.from_bytes(m.ler_memoria(Z_ + 2 * i, 2), "little"), 16)
            self.assertLess(abs(conv - orig) / abs(orig), 1e-2)

    def test_produto_escalar_t8_em_memoria(self):
        X_, Y_, ACC_, Z_ = 0x100, 0x200, 0x300, 0x400
        m = Maquina()
        m.carregar_programa(montar([
            f"li a0, {X_}", f"li a1, {Y_}", f"li a2, {ACC_}", f"li a3, {Z_}",
            "li t1, 2",
            "vsetvli t0, t1, e32, m1, ta, ma",
            "vle32.v v1, (a0)", "vle32.v v2, (a1)", "vle32.v v3, (a2)",
            "vtdot8.vv v3, v2, v1",
            "li t1, 1",
            "vsetvli t0, t1, e32, m1, ta, ma",
            "vse32.v v3, (a3)",
        ]))
        X = [1.5, 2.0, -3.0, 0.5, 1.0, 2.0, 3.0, 4.0]
        Y = [2.25, 4.0, 1.0, 0.5, 1.0, 0.5, 0.5, 0.25]
        for i in range(8):
            m.escrever_memoria(X_ + i, T(X[i], 8).to_bytes(1, "little"))
            m.escrever_memoria(Y_ + i, T(Y[i], 8).to_bytes(1, "little"))
        m.escrever_memoria(ACC_, T(10.0, 32).to_bytes(4, "little"))
        executar(m)
        bits = int.from_bytes(m.ler_memoria(Z_, 4), "little")
        esperado = 10 + sum(a * b for a, b in zip(X, Y))   # 23.125
        self.assertProximo(F(bits, 32), esperado, rel=0.1)  # T8 introduz erro nas entradas

    def test_limite_de_ciclos(self):
        m = Maquina()
        m.carregar_programa(montar(["laco:", "li t0, 1", "bnez t0, laco"]))
        with self.assertRaises(RuntimeError):
            executar(m, max_ciclos=50)


if __name__ == "__main__":
    unittest.main(verbosity=2)