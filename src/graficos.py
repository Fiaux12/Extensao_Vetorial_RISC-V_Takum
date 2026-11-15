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

DECADAS = range(5)          # k = 0..4  ->  [1, 10], ..., [10^4, 10^5]
TAMANHO = 100               # matriz quadrada fixa

def plotar_grafico(resultados: dict, descricao: str = "", arquivo: str | None = None) -> None:
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
    ax.set_title(f"{rotulo} do erro relativo de y = A.x")
    ax.grid(alpha=0.3)
    ax.legend(ncol=2)
    fig.tight_layout()
    if arquivo:
        fig.savefig(arquivo, dpi=150)
        print(f"gráfico salvo em {arquivo}")
        plt.close(fig)
    else:
        plt.show()


def coletar_erros_relativos(tamanho: int = 100, esparsidade: float = ESPARSIDADE,
                            semente: int = SEMENTE, repeticoes: int = 3) -> dict:
    """Erro relativo de cada linha de y (todas as repetições juntas), por formato.
    Usa a mesma semente de varrer_tamanhos, então os dados são os mesmos dos
    gráficos por tamanho."""
    erros = {f"{p}{w}": [] for w in LARGURAS for p in ("T", "FP")}
    for r in range(repeticoes):
        A, x = gerar_dados(tamanho, tamanho, esparsidade, semente + 1000 * tamanho + r)
        y_ref = calcular_referencia(A, x)
        for w in LARGURAS:
            erros[f"T{w}"] += erro_relativo(executar_takum(A, x, w), y_ref)[0]
            erros[f"FP{w}"] += erro_relativo(calcular_padrao(A, x, w), y_ref)[0]
    return erros


def plotar_violino(erros: dict, tamanho: int, arquivo: str | None = None) -> None:
    """Violin plot de log10(erro relativo), um violino por formato, Takum e IEEE
    lado a lado em cada largura. Traço preto = mediana; losango = média (a mesma
    média do gráfico por tamanho). O n sob cada rótulo é o número de linhas
    plotadas: erros iguais a zero ou infinitos não têm log e ficam de fora."""
    import matplotlib
    if arquivo:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    cor = {"T": "#1f77b4", "FP": "#ff7f0e"}
    fig, ax = plt.subplots(figsize=(9, 5.5))
    posicoes, rotulos = [], []

    for g, w in enumerate(LARGURAS):
        for deslocamento, prefixo in ((-0.2, "T"), (0.2, "FP")):
            nome = f"{prefixo}{w}"
            validos = [e for e in erros[nome] if 0 < e < math.inf]
            pos = g + 1 + deslocamento
            posicoes.append(pos)
            rotulos.append(f"{nome}\n(n={len(validos)})")
            if len(validos) < 2:
                continue
            logs = np.log10(validos)

            partes = ax.violinplot(logs, positions=[pos], widths=0.36, showextrema=False)
            for corpo in partes["bodies"]:
                corpo.set_facecolor(cor[prefixo])
                corpo.set_edgecolor(cor[prefixo])
                corpo.set_alpha(0.55)

            ax.hlines(float(np.median(logs)), pos - 0.14, pos + 0.14, color="black", lw=2)
            media = float(np.mean(erros[nome]))
            if 0 < media < math.inf:
                ax.scatter([pos], [math.log10(media)], marker="D", s=28, zorder=3,
                           color="white", edgecolor="black")

    ax.set_xticks(posicoes)
    ax.set_xticklabels(rotulos)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$10^{{{v:.0f}}}$"))
    ax.set_ylabel("Erro relativo (escala log)")
    ax.set_title(f"Distribuição do erro relativo de y = A.x ({tamanho}×{tamanho})")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=cor["T"], alpha=0.55),
                       plt.Rectangle((0, 0), 1, 1, color=cor["FP"], alpha=0.55),
                       Line2D([0], [0], color="black", lw=2),
                       Line2D([0], [0], marker="D", color="none", markerfacecolor="white",
                              markeredgecolor="black")],
              labels=["Takum", "IEEE 754", "Mediana", "Média"], loc="upper right", ncol=2)
    fig.tight_layout()
    if arquivo:
        fig.savefig(arquivo, dpi=150)
        print(f"gráfico salvo em {arquivo}")
        plt.close(fig)
    else:
        plt.show()


def gerar_violino(arquivo: str | None = None, tamanho: int = 100,
                  repeticoes: int = 3) -> None:
    """Roda os seis formatos em uma matriz tamanho x tamanho e faz o violin plot."""
    erros = coletar_erros_relativos(tamanho, repeticoes=repeticoes)
    plotar_violino(erros, tamanho, arquivo)


def escalar_dados(A: list, x: list, k: int):
    """Mantém o padrão de zeros e a semente: cada módulo |a| em [0, 1) vira
    10^(k + |a|), log-uniforme em [10^k, 10^(k+1)). Tudo positivo (sem cancelamento).
    x fica em [0, 1], assim só A muda de escala."""
    A_k = [[10 ** (k + abs(a)) if a != 0.0 else 0.0 for a in linha] for linha in A]
    return A_k, [abs(v) for v in x]


def varrer_escala(decadas=DECADAS, tamanho: int = TAMANHO,
                  esparsidade: float = ESPARSIDADE, semente: int = SEMENTE) -> dict:
    """curvas[formato] = lista com a mediana do erro relativo em cada década."""
    A0, x0 = gerar_dados(tamanho, tamanho, esparsidade, semente)   # mesma base em todas as décadas
    curvas = {f"{p}{w}": [] for p in ("T", "FP") for w in LARGURAS}
    for k in decadas:
        A, x = escalar_dados(A0, x0, k)
        y_ref = calcular_referencia(A, x)
        with np.errstate(over="ignore"):                  # FP16 estoura para inf: esperado
            for w in LARGURAS:
                for nome, y in ((f"T{w}", executar_takum(A, x, w)),
                                (f"FP{w}", calcular_padrao(A, x, w))):
                    erros = erro_relativo(y, y_ref)[0]
                    curvas[nome].append(float(np.median(erros)) if erros else float("nan"))
    return curvas


def plotar_escala(curvas: dict, decadas, arquivo: str | None = None) -> None:
    import matplotlib
    if arquivo:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ks = list(decadas)
    cor = {8: "#d62728", 16: "#1f77b4", 32: "#2ca02c"}
    fig, ax = plt.subplots(figsize=(8, 5))
    for w in LARGURAS:
        ax.plot(ks, curvas[f"T{w}"], "-o", color=cor[w], label=f"T{w}")
        ax.plot(ks, curvas[f"FP{w}"], "--s", color=cor[w], label=f"FP{w}")
    ax.set_yscale("log")
    ax.set_xticks(ks)
    ax.set_xticklabels([f"$10^{{{k}}}$–$10^{{{k + 1}}}$" for k in ks])
    ax.set_xlabel("Faixa dos módulos de A")
    ax.set_ylabel("Mediana do erro relativo (escala log)")
    ax.set_title("Mediana do erro relativo de y = A.x por escala de A")
    ax.grid(alpha=0.3)
    ax.legend(ncol=2)
    fig.tight_layout()
    if arquivo:
        fig.savefig(arquivo, dpi=150)
        print(f"gráfico salvo em {arquivo}")
        plt.close(fig)
    else:
        plt.show()

def gerar_graficos_por_tamanho(arquivo_mediana: str | None = "mediana",
                               arquivo_media: str | None = "media",
                               repeticoes: int = 3) -> None:
    """Roda a varredura (10 a 100, de 10 em 10) e faz os dois gráficos."""
    curvas = varrer_tamanhos(TAMANHOS, repeticoes=repeticoes)
    plotar_erro_por_tamanho(curvas, TAMANHOS, "mediana", arquivo_mediana)
    plotar_erro_por_tamanho(curvas, TAMANHOS, "media", arquivo_media)
    gerar_violino("violino", )
    plotar_escala(varrer_escala(), DECADAS, "escala.png")
    print(f"Concluído!!!")
