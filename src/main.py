"""
main.py
Ciclo buscar -> decodificar -> executar e demonstração.

Executar:  python main.py
"""
from estruturas import Maquina
from codificacao import identificar, codificar
from instrucoes import TABELA_EXEC


def ciclo(m: Maquina, contador=None) -> None:
    """Um ciclo do caminho de dados."""
    palavra = m.buscar_instrucao()          # BUSCAR   (PC -> memória de instruções)
    nome, campos = identificar(palavra)     # DECODIFICAR (unidade de controle)
    if contador is not None:
        contador[nome] += 1                 # contagem dinâmica por mnemônico
    desviou = TABELA_EXEC[nome](m, campos)  # EXECUTAR (banco de registradores + ULA)
    if not desviou:
        m.pc += 4


def executar(m: Maquina, max_ciclos: int = 100_000, contador=None) -> None:
    n = 0
    while not m.fim_do_programa():
        ciclo(m, contador)
        n += 1
        if n >= max_ciclos:
            raise RuntimeError("limite de ciclos atingido (laço infinito?)")


def main() -> None:
    m = Maquina()

    # Teste da codificação: vtmul.vv v1, v2, v3  ->  0x922190AB
    palavra = codificar("vtmul.vv", 1, 2, 3)
    print(f"vtmul.vv v1, v2, v3 = 0x{palavra:08X}")
    nome, campos = identificar(palavra)
    print(nome, campos)

    # Quando as instruções estiverem implementadas:
    # m.carregar_programa([...palavras...])
    # executar(m)

if __name__ == "__main__":
    main()