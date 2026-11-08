import math
import random
import sys
from decimal import Decimal, localcontext
import numpy as np

from experimennto import gerar_dados, executar_takum, calcular_padrao, calcular_referencia, erro_relativo

TAMANHOS = list(range(10, 101, 10))       # matrizes quadradas 10x10, 20x20, ..., 100x100
LINHAS = 16
COLUNAS = 32
ESPARSIDADE = 0.7           # fração de zeros em A
SEMENTE = 42
LARGURAS = (8, 16, 32)    

def plotar_grafico(resultados: dict, descricao: str = "", arquivo: str | None = None) -> None:
    """Gráfico com os mesmos dados de imprimir_tabela: três painéis (erro absoluto
    médio, erro relativo médio e mediana do erro absoluto), uma barra por formato.
    Escala logarítmica, porque os erros variam em várias ordens de grandeza.
    Se `arquivo` for dado, salva a figura nele; senão, abre a janela."""
    import matplotlib
    if arquivo:
        matplotlib.use("Agg")                       # sem janela: só grava o arquivo
    import matplotlib.pyplot as plt

    nomes = list(resultados)
    metricas = [
        ("Erro absoluto (média)",
         [float(np.mean(a)) for a, _, _ in resultados.values()]),
        ("Erro relativo (média)",
         [float(np.mean(r)) if r else math.nan for _, r, _ in resultados.values()]),
        ("Mediana do erro absoluto",
         [float(np.median(a)) for a, _, _ in resultados.values()]),
    ]
    cores = ["#1f77b4" if nome.startswith("T") else "#ff7f0e" for nome in nomes]

    fig, eixos = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, (titulo, valores) in zip(eixos, metricas):
        barras = ax.bar(nomes, valores, color=cores)
        ax.set_yscale("log")
        ax.set_title(titulo)
        ax.set_ylabel("erro (escala log)")
        ax.grid(axis="y", alpha=0.3)
        ax.bar_label(barras, labels=[f"{v:.1e}" for v in valores], fontsize=7, padding=2)
        ax.set_ylim(top=max(valores) * 6)           # espaço para os rótulos
        ax.tick_params(axis="x", labelrotation=45)
    eixos[0].legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#1f77b4"),
                             plt.Rectangle((0, 0), 1, 1, color="#ff7f0e")],
                    labels=["Takum", "IEEE 754"], loc="upper right")
    fig.suptitle(f"Erro de y = A.x contra a referência ({descricao})")
    fig.tight_layout()
    if arquivo:
        fig.savefig(arquivo, dpi=150)
        print(f"gráfico salvo em {arquivo}")
        plt.close(fig)
    else:
        plt.show()



def varrer_tamanhos(tamanhos=TAMANHOS, esparsidade: float = ESPARSIDADE,
                    semente: int = SEMENTE, repeticoes: int = 3) -> dict:
    curvas = {f"{p}{w}": {"mediana": [], "media": []}
              for p in ("T", "FP") for w in LARGURAS}
    for t in tamanhos:
        erros = {nome: [] for nome in curvas}
        for r in range(repeticoes):
            A, x = gerar_dados(t, t, esparsidade, semente + 1000 * t + r)
            y_ref = calcular_referencia(A, x)
            for w in LARGURAS:
                for nome, y in ((f"T{w}", executar_takum(A, x, w)),
                                (f"FP{w}", calcular_padrao(A, x, w))):
                    erros[nome] += erro_relativo(y, y_ref)[0]
        for nome, e in erros.items():
            curvas[nome]["mediana"].append(float(np.median(e)) if e else math.nan)
            curvas[nome]["media"].append(float(np.mean(e)) if e else math.nan)
        print(f"  tamanho {t}x{t} concluído")
    return curvas


def plotar_erro_por_tamanho(curvas: dict, tamanhos: list, metrica: str = "mediana",
                            arquivo: str | None = None) -> None:
    import matplotlib
    if arquivo:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rotulo = {"mediana": "Mediana", "media": "Média"}[metrica]
    cor = {8: "#d62728", 16: "#1f77b4", 32: "#2ca02c"}

    fig, ax = plt.subplots(figsize=(8, 5))
    for w in LARGURAS:
        ax.plot(tamanhos, curvas[f"T{w}"][metrica], "-o", color=cor[w], label=f"T{w}")
        ax.plot(tamanhos, curvas[f"FP{w}"][metrica], "--s", color=cor[w], label=f"FP{w}")
    ax.set_yscale("log")
    ax.set_xticks(tamanhos)
    ax.set_xlabel("Tamanho da matriz (N × N)")
    ax.set_ylabel(f"{rotulo} do erro relativo (escala log)")
    ax.set_title(f"{rotulo} do erro relativo de y = A.x: Takum (—) x IEEE 754 (- -)")
    ax.grid(alpha=0.3)
    ax.legend(ncol=2)
    fig.tight_layout()
    if arquivo:
        fig.savefig(arquivo, dpi=150)
        print(f"gráfico salvo em {arquivo}")
        plt.close(fig)
    else:
        plt.show()


def gerar_graficos_por_tamanho(arquivo_mediana: str | None = None,
                               arquivo_media: str | None = None,
                               repeticoes: int = 3) -> None:
    """Roda a varredura (10 a 100, de 10 em 10) e faz os dois gráficos."""
    curvas = varrer_tamanhos(TAMANHOS, repeticoes=repeticoes)
    plotar_erro_por_tamanho(curvas, TAMANHOS, "mediana", arquivo_mediana)
    plotar_erro_por_tamanho(curvas, TAMANHOS, "media", arquivo_media)