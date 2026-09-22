"""Figuras da Questão 1. Cada figura explica o algoritmo (não é decorativa).

* ``figura_grafo``            Figura 1 — rede, pesos e vias bloqueadas
* ``figura_solucoes``         Figura 2 — atendidos x não atendidos + sequência da rota
* ``figura_dp``               Figura 3 — heatmap da DP, trilha da reconstrução e evolução do benefício
* ``figura_greedy_vs_dp``     Figura 4 — benefício por capacidade (Parte D)
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from .comparacao import LinhaComparacao
from .dynamic_programming import ResultadoDP
from .estruturas import CENTRO, GrafoLogistico, Solucao
from .grafos import TabelaDistancias

COR_VIA = "#9aa0a6"
COR_BLOQUEADA = "#d93025"
COR_ATENDIDO = "#188038"
COR_NAO_ATENDIDO = "#ffffff"
COR_CENTRO = "#1a73e8"
CORES_METODO = {"Guloso": "#e8710a", "Programação Dinâmica": "#188038"}


def _salvar(fig: plt.Figure, salvar_em: str | Path | None) -> None:
    if salvar_em is not None:
        Path(salvar_em).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(salvar_em, dpi=150, bbox_inches="tight")


def _desenhar_vias(ax: plt.Axes, grafo: GrafoLogistico, rotulos: bool = True) -> None:
    for a in grafo.arestas():
        p, q = grafo.ponto(a.origem), grafo.ponto(a.destino)
        if a.disponivel:
            ax.plot([p.x, q.x], [p.y, q.y], color=COR_VIA, lw=1.1, zorder=1)
        else:
            ax.plot([p.x, q.x], [p.y, q.y], color=COR_BLOQUEADA, lw=1.6, ls="--", zorder=1)
        if rotulos:
            texto = f"{a.distancia:.0f}" if a.disponivel else f"×{a.distancia:.0f}"
            ax.text((p.x + q.x) / 2, (p.y + q.y) / 2, texto, fontsize=6.5, ha="center",
                    va="center", color="#3c4043" if a.disponivel else COR_BLOQUEADA,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85),
                    zorder=2)


def _desenhar_centro(ax: plt.Axes, grafo: GrafoLogistico) -> None:
    c = grafo.ponto(CENTRO)
    ax.scatter([c.x], [c.y], marker="s", s=260, c=COR_CENTRO, edgecolors="black",
               linewidths=1, zorder=4)
    ax.text(c.x, c.y, "CD", color="white", fontsize=7.5, ha="center", va="center",
            weight="bold", zorder=5)


def _formatar_eixos(ax: plt.Axes) -> None:
    ax.set_aspect("equal")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.grid(alpha=0.15)


def figura_grafo(grafo: GrafoLogistico, salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 1 — centro, pontos (cor = prioridade, tamanho = pessoas), vias e bloqueios."""
    fig, ax = plt.subplots(figsize=(12, 9.5))
    _desenhar_vias(ax, grafo)
    pontos = grafo.pontos_atendimento()
    sc = ax.scatter([p.x for p in pontos], [p.y for p in pontos],
                    c=[p.prioridade for p in pontos], cmap="YlOrRd", vmin=0.5, vmax=5.5,
                    s=[90 + 0.9 * p.pessoas for p in pontos], edgecolors="black",
                    linewidths=0.8, zorder=3)
    for p in pontos:
        ax.text(p.x, p.y, str(p.id), ha="center", va="center", fontsize=7.5, weight="bold", zorder=5)
    _desenhar_centro(ax, grafo)
    cbar = fig.colorbar(sc, ax=ax, ticks=[1, 2, 3, 4, 5], shrink=0.7)
    cbar.set_label("Prioridade (1 = baixa, 5 = crítica)")
    legenda = [
        Line2D([0], [0], color=COR_VIA, lw=1.5, label="via disponível (peso = km)"),
        Line2D([0], [0], color=COR_BLOQUEADA, lw=1.8, ls="--", label="via bloqueada (×km)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COR_CENTRO, markeredgecolor="k",
               markersize=11, label="centro de distribuição"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#fdae61", markeredgecolor="k",
               markersize=9, label="ponto (tamanho ∝ pessoas afetadas)"),
    ]
    ax.legend(handles=legenda, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2,
              fontsize=8, framealpha=0.95)
    ax.set_title(f"Figura 1 — Rede logística: {len(pontos)} pontos, "
                 f"{grafo.num_arestas_disponiveis} vias disponíveis, "
                 f"{grafo.num_arestas_bloqueadas} bloqueadas")
    _formatar_eixos(ax)
    _salvar(fig, salvar_em)
    return fig


def _desenhar_rota(ax: plt.Axes, grafo: GrafoLogistico, ordem: Sequence[int],
                   tabela: TabelaDistancias, cor: str) -> None:
    """Desenha a rota CD -> ordem -> CD seguindo os caminhos mínimos reais do grafo."""
    paradas = [CENTRO, *ordem, CENTRO] if ordem else []
    for origem, destino in zip(paradas, paradas[1:]):
        caminho = tabela.caminho(origem, destino)
        for u, v in zip(caminho, caminho[1:]):
            p, q = grafo.ponto(u), grafo.ponto(v)
            ax.annotate("", xy=(q.x, q.y), xytext=(p.x, p.y), zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=cor, lw=2.2, alpha=0.85,
                                        shrinkA=7, shrinkB=7))


def figura_solucoes(grafo: GrafoLogistico, solucoes: Sequence[Solucao], tabela: TabelaDistancias,
                    capacidade: int, titulo: str = "Figura 2 — Soluções encontradas",
                    salvar_em: str | Path | None = None,
                    rotulos_vias: bool = False) -> plt.Figure:
    """Figura 2 — um painel por solução: verde = atendido (número = ordem), branco = não atendido."""
    fig, eixos = plt.subplots(1, len(solucoes), figsize=(9.5 * len(solucoes), 8.5), squeeze=False)
    for ax, sol in zip(eixos[0], solucoes):
        cor_rota = CORES_METODO.get(sol.nome, "#1a73e8")
        _desenhar_vias(ax, grafo, rotulos=rotulos_vias)
        _desenhar_rota(ax, grafo, sol.ordem, tabela, cor_rota)
        ordem_de = {j: k for k, j in enumerate(sol.ordem, start=1)}
        for p in grafo.pontos_atendimento():
            atendido = p.id in ordem_de
            ax.scatter([p.x], [p.y], s=330, zorder=4, edgecolors="black" if atendido else "#5f6368",
                       linewidths=1.2, facecolors=COR_ATENDIDO if atendido else COR_NAO_ATENDIDO)
            ax.text(p.x, p.y, str(p.id), ha="center", va="center", fontsize=7.5, zorder=5,
                    weight="bold", color="white" if atendido else "#5f6368")
            if atendido:
                ax.annotate(f"#{ordem_de[p.id]}", (p.x, p.y), xytext=(11, 11),
                            textcoords="offset points", fontsize=9, weight="bold", color=cor_rota,
                            zorder=6, bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                                ec=cor_rota, lw=0.8))
        _desenhar_centro(ax, grafo)
        ax.set_title(f"{sol.nome}\nbenefício = {sol.beneficio} | carga = {sol.carga}/{capacidade} kg | "
                     f"rota = {sol.distancia:.1f} km | {len(sol.ordem)} atendidos")
        _formatar_eixos(ax)
    legenda = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COR_ATENDIDO, markeredgecolor="k",
               markersize=11, label="atendido (#n = ordem da visita)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor="#5f6368",
               markersize=11, label="não atendido"),
        Line2D([0], [0], color=COR_VIA, lw=1.2, label="via (não usada)"),
        Line2D([0], [0], color=COR_BLOQUEADA, lw=1.6, ls="--", label="via bloqueada"),
    ]
    fig.legend(handles=legenda, loc="lower center", ncol=4, fontsize=9, framealpha=0.95)
    fig.suptitle(titulo, fontsize=13, y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _salvar(fig, salvar_em)
    return fig


def _trilha_reconstrucao(resultado: ResultadoDP) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Pontos (c, i) percorridos pela reconstrução e pontos onde a região foi atendida."""
    tabela, pesos = resultado.tabela, resultado.pesos
    c = resultado.capacidade
    trilha = [(c, len(pesos))]
    tomadas = []
    for i in range(len(pesos), 0, -1):
        if tabela[i][c] != tabela[i - 1][c]:
            tomadas.append((c, i))
            c -= pesos[i - 1]
        trilha.append((c, i - 1))
    return trilha, tomadas


def figura_dp(resultado: ResultadoDP, salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 3 — (a) heatmap DP[i][c] + trilha da reconstrução; (b) DP[i][C]; (c) DP[N][c]."""
    tabela = np.array(resultado.tabela)
    n, cap = len(resultado.pesos), resultado.capacidade
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 7.5),
                                        gridspec_kw={"width_ratios": [2.3, 1, 1]})

    im = ax1.imshow(tabela, aspect="auto", origin="lower", cmap="viridis",
                    extent=(-0.5, cap + 0.5, -0.5, n + 0.5))
    trilha, tomadas = _trilha_reconstrucao(resultado)
    ax1.plot([c for c, _ in trilha], [i for _, i in trilha], color="white", lw=1.6,
             label="trilha da reconstrução")
    ax1.scatter([c for c, _ in tomadas], [i for _, i in tomadas], marker="*", s=170,
                c="red", edgecolors="white", zorder=5, label="região atendida (DP[i][c] ≠ DP[i-1][c])")
    ax1.set_yticks(range(n + 1))
    ax1.set_yticklabels(["0 (base)"] + [f"{i}: P{resultado.candidatas[i - 1]:02d}" for i in range(1, n + 1)],
                        fontsize=7)
    ax1.set_xlabel("capacidade disponível c (kg)")
    ax1.set_ylabel("regiões consideradas i")
    ax1.set_title("(a) Tabela DP[i][c] — benefício máximo; a trilha parte de (N, C)")
    ax1.legend(loc="upper left", fontsize=8)
    fig.colorbar(im, ax=ax1, label="benefício acumulado")

    evolucao = tabela[:, cap]
    ax2.step(range(n + 1), evolucao, where="post", color=CORES_METODO["Programação Dinâmica"], lw=2)
    ax2.scatter(range(n + 1), evolucao, s=18, color=CORES_METODO["Programação Dinâmica"])
    ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.set_xlabel("regiões consideradas i")
    ax2.set_ylabel(f"DP[i][C={cap}]")
    ax2.set_title("(b) Evolução do benefício ao\nconsiderar cada nova região")
    ax2.grid(alpha=0.3)

    ax3.plot(range(cap + 1), tabela[n], color="#1a73e8", lw=2)
    ax3.scatter([cap], [tabela[n][cap]], color="red", zorder=5, s=50,
                label=f"ótimo em C={cap}: {tabela[n][cap]}")
    ax3.set_xlabel("capacidade c (kg)")
    ax3.set_ylabel(f"DP[N={n}][c]")
    ax3.set_title("(c) Benefício ótimo por capacidade\n(última linha da tabela)")
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3)

    fig.suptitle("Figura 3 — Programação Dinâmica (mochila 0/1)", fontsize=13)
    fig.tight_layout()
    _salvar(fig, salvar_em)
    return fig


def figura_greedy_vs_dp(linhas: Sequence[LinhaComparacao], capacidade_principal: int | None = None,
                        salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 4 — benefício de cada método e diferença (DP − guloso) por capacidade."""
    caps = [l.capacidade for l in linhas]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    ax1.plot(caps, [l.beneficio_dp for l in linhas], color=CORES_METODO["Programação Dinâmica"],
             lw=2.4, label="Programação Dinâmica (ótimo)")
    ax1.plot(caps, [l.beneficio_guloso for l in linhas], color=CORES_METODO["Guloso"], lw=1.8,
             ls="--", label="Guloso")
    ax2.bar(caps, [l.diferenca for l in linhas],
            width=(caps[1] - caps[0]) * 0.8 if len(caps) > 1 else 1,
            color=[CORES_METODO["Guloso"] if l.diferenca else "#bdc1c6" for l in linhas])
    if capacidade_principal is not None:
        for ax in (ax1, ax2):
            ax.axvline(capacidade_principal, color="black", ls=":", lw=1.2)
        ax1.text(capacidade_principal, ax1.get_ylim()[0], " capacidade da instância",
                 rotation=90, va="bottom", ha="right", fontsize=8)
    iguais = sum(l.guloso_otimo for l in linhas)
    ax1.set_ylabel("benefício total")
    ax1.set_title(f"Figura 4 — Guloso × DP variando a capacidade "
                  f"(guloso ótimo em {iguais}/{len(linhas)} capacidades)")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax2.set_ylabel("DP − guloso")
    ax2.set_xlabel("capacidade do veículo (kg)")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    _salvar(fig, salvar_em)
    return fig
