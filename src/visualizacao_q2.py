"""Figuras da Questão 2.

* ``figura_serie_temporal``          Figura 1 — consumo x tempo + intervalo crítico
* ``figura_divide_conquer``          Figura 2 — 4 níveis da decomposição, sobre os dados reais
* ``figura_escalabilidade``          Figura 3 — tamanho da entrada x tempo (e operações)
* ``figura_estruturas``              Figura 4 — consultas da Parte A (região, hora do dia, períodos críticos)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from .divide_conquer import NoRecursao
from .escalabilidade import LinhaEscalabilidade, estimar_expoente
from .estruturas_energia import ESCALA, IndiceEnergia
from .intervalos import ResultadoIntervalo

COR_CONSUMO = "#1a73e8"
COR_CAPACIDADE = "#5f6368"
COR_CRITICO = "#d93025"
COR_ESQ, COR_DIR, COR_CRUZ = "#1a73e8", "#f9ab00", "#d93025"
CORES_ALGORITMO = {"Força bruta O(n³)": "#a50e0e", "Força bruta O(n²)": "#e8710a",
                   "Dividir e Conquistar": "#188038"}


def _salvar(fig: plt.Figure, salvar_em: str | Path | None) -> None:
    if salvar_em is not None:
        Path(salvar_em).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(salvar_em, dpi=150, bbox_inches="tight")


def _rotulos_de_dia(ax: plt.Axes, indice: IndiceEnergia, passo_horas: int = 96) -> None:
    ticks = list(range(0, len(indice.timestamps), passo_horas))
    ax.set_xticks(ticks)
    ax.set_xticklabels([indice.timestamps[i].strftime("%d/%m") for i in ticks])


def figura_serie_temporal(indice: IndiceEnergia, intervalo: ResultadoIntervalo,
                          salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 1 — (a) consumo e capacidade do sistema; (b) criticidade por hora; intervalo crítico sombreado."""
    horas = range(len(indice.serie))
    t0, t1 = indice.timestamps[intervalo.inicio], indice.timestamps[intervalo.fim]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1.2]})
    ax1.plot(horas, [p.consumo for p in indice.serie], color=COR_CONSUMO, lw=1.1, label="consumo do sistema (MWh)")
    ax1.plot(horas, [p.capacidade for p in indice.serie], color=COR_CAPACIDADE, lw=1, ls="--",
             label="capacidade disponível (MWh)")
    picos = indice.top_picos(3)
    ax1.scatter([p.indice for p in picos], [p.consumo for p in picos], color="black", zorder=5, s=25,
                label="3 maiores picos (heap)")
    ax1.set_ylabel("MWh por hora")
    ax1.set_title(f"Figura 1 — Consumo × tempo e intervalo crítico encontrado "
                  f"({t0:%d/%m %Hh} → {t1:%d/%m %Hh}, {intervalo.tamanho} h, criticidade acumulada "
                  f"{intervalo.soma / ESCALA:,.0f})")
    barras = [p.criticidade / ESCALA for p in indice.serie]
    ax2.bar(horas, barras, width=1.0, color=[COR_CRITICO if b > 0 else "#9aa0a6" for b in barras])
    ax2.axhline(0, color="black", lw=0.6)
    ax2.set_ylabel("criticidade da hora\n(vermelho > 0: pressão)")
    ax2.set_xlabel("data")
    for ax in (ax1, ax2):
        ax.axvspan(intervalo.inicio - 0.5, intervalo.fim + 0.5, color=COR_CRITICO, alpha=0.18)
        ax.grid(alpha=0.25)
    ax1.legend(handles=[*ax1.get_legend_handles_labels()[0],
                        Patch(color=COR_CRITICO, alpha=0.3, label="intervalo crítico (maior soma contínua)")],
               loc="upper left", fontsize=8)
    _rotulos_de_dia(ax2, indice)
    fig.tight_layout()
    _salvar(fig, salvar_em)
    return fig


def _origem_do_melhor(no: NoRecursao) -> str:
    if no.melhor == no.cruzado:
        return "cruzado"
    return "esquerda" if no.melhor == no.esquerda else "direita"


def figura_divide_conquer(indice: IndiceEnergia, trace: Sequence[NoRecursao], resultado: ResultadoIntervalo,
                          niveis: int = 4, salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 2 — decomposição nos ``niveis`` primeiros níveis, com os dados processados de verdade.

    Cada painel é um nível: 2^k subproblemas separados por linhas tracejadas; em cada um, a
    faixa colorida é o melhor intervalo do subproblema e a cor diz de onde ele veio
    (metade esquerda, metade direita ou caso que atravessa o meio).
    """
    serie = [p.criticidade / ESCALA for p in indice.serie]
    n = len(serie)
    por_nivel: dict[int, list[NoRecursao]] = {}
    for no in trace:
        por_nivel.setdefault(no.nivel, []).append(no)
    fig, eixos = plt.subplots(niveis, 1, figsize=(15, 2.6 * niveis), sharex=True)
    lim = (min(serie) * 1.15, max(serie) * 1.35)
    cores = {"esquerda": COR_ESQ, "direita": COR_DIR, "cruzado": COR_CRUZ}
    for nivel, ax in enumerate(eixos):
        ax.plot(range(n), serie, color="#5f6368", lw=0.7)
        ax.axhline(0, color="black", lw=0.5)
        nos = sorted(por_nivel.get(nivel, []), key=lambda x: x.lo)
        for no in nos:
            soma, i, j = no.melhor
            cor = cores[_origem_do_melhor(no)]
            ax.axvspan(i - 0.5, j + 0.5, color=cor, alpha=0.35)
            ax.axvline(no.lo - 0.5, color="black", ls=":", lw=0.8)
            ax.axvline(no.mid + 0.5, color="black", ls="--", lw=0.7, alpha=0.6)  # DIVIDE
            ax.text((no.lo + no.hi) / 2, lim[1] * 0.93, f"Σ={soma / ESCALA:,.0f}", ha="center", va="top",
                    fontsize=8, weight="bold", color=cor)
        ax.axvline(n - 0.5, color="black", ls=":", lw=0.8)
        ax.set_ylim(*lim)
        ax.set_ylabel(f"nível {nivel}\n{2 ** nivel} subproblema(s)", fontsize=9)
        ax.grid(alpha=0.15)
    raiz = por_nivel[0][0]
    altura = lim[1] - lim[0]
    for k, (cand, rotulo, cor) in enumerate(((raiz.esquerda, "esq.", COR_ESQ), (raiz.direita, "dir.", COR_DIR),
                                             (raiz.cruzado, "cruz.", COR_CRUZ))):  # 3 candidatos da raiz
        y = lim[0] + altura * (0.06 + 0.07 * k)
        eixos[0].hlines(y, cand[1] - 0.5, cand[2] + 0.5, color=cor, lw=3)
        eixos[0].text(cand[2] + 6, y, f"{rotulo} Σ={cand[0] / ESCALA:,.0f}", fontsize=7, va="center", color=cor)
    fig.legend(handles=[
        Patch(color=COR_ESQ, alpha=0.5, label="melhor veio da metade esquerda (SOLVE LEFT)"),
        Patch(color=COR_DIR, alpha=0.5, label="melhor veio da metade direita (SOLVE RIGHT)"),
        Patch(color=COR_CRUZ, alpha=0.5, label="melhor atravessa o meio (SOLVE CROSSING)"),
    ], loc="lower center", fontsize=9, ncol=3, bbox_to_anchor=(0.5, -0.005))
    _rotulos_de_dia(eixos[-1], indice)
    eixos[-1].set_xlabel("data (linha tracejada = ponto de divisão 'mid'; barras horizontais no nível 0 = 3 candidatos da raiz)")
    fig.suptitle(f"Figura 2 — Dividir e Conquistar sobre {n} horas reais: resultado final = "
                 f"[{resultado.inicio}, {resultado.fim}] com Σ={resultado.soma / ESCALA:,.0f} "
                 f"(profundidade {resultado.profundidade})", fontsize=12)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    _salvar(fig, salvar_em)
    return fig


def figura_escalabilidade(linhas: Sequence[LinhaEscalabilidade],
                          salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 3 — (a) tempo x n; (b) operações x n; escala log-log com inclinações estimadas."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    for nome, cor in CORES_ALGORITMO.items():
        pts = [(l.n, l.tempo_s, l.operacoes) for l in linhas if l.algoritmo == nome]
        if len(pts) < 2:
            continue
        ns, ts, ops = zip(*pts)
        expoente = estimar_expoente(ns, ts)
        ax1.plot(ns, ts, "o-", color=cor, lw=2, label=f"{nome} (T ∝ n^{expoente:.2f})")
        ax2.plot(ns, ops, "o-", color=cor, lw=2, label=nome)
    ns_ref = sorted({l.n for l in linhas})
    ax2.plot(ns_ref, [n * (n + 1) // 2 for n in ns_ref], ":", color="black", lw=1, label="n(n+1)/2 (teórico)")
    ax2.plot(ns_ref, [n * (math.ceil(math.log2(n)) + 1) for n in ns_ref], "--", color="black", lw=1,
             label="n(⌈log₂n⌉+1) (teórico)")
    for ax, titulo, ylabel in ((ax1, "(a) Tempo médio de execução", "tempo (s)"),
                               (ax2, "(b) Operações relevantes contadas", "somas/comparações")):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("tamanho da entrada n (horas)")
        ax.set_ylabel(ylabel)
        ax.set_title(titulo)
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8)
    fig.suptitle("Figura 3 — Escalabilidade: força bruta × dividir e conquistar (eixos log-log)")
    fig.tight_layout()
    _salvar(fig, salvar_em)
    return fig


def figura_estruturas(indice: IndiceEnergia, limiar: float = 0.90,
                      salvar_em: str | Path | None = None) -> plt.Figure:
    """Figura 4 — (a) consumo por região; (b) perfil por hora do dia; (c) períodos críticos por região."""
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(19, 5.5), gridspec_kw={"width_ratios": [1, 1.2, 1.8]})
    totais = indice.consumo_total_por_regiao()
    ax1.bar(list(totais), [v / 1000 for v in totais.values()], color=COR_CONSUMO)
    ax1.set_ylabel("consumo total (GWh)")
    ax1.set_title("(a) Consumo por região\n(dict região → índices)")
    ax1.tick_params(axis="x", rotation=25)
    for regiao in sorted(indice.regioes):
        perfil = indice.perfil_horario(regiao)
        ax2.plot(list(perfil), list(perfil.values()), marker="o", ms=3, label=regiao)
    ax2.set_xlabel("hora do dia")
    ax2.set_ylabel("consumo médio por unidade-hora (MWh)")
    ax2.set_title("(b) Perfil por hora do dia\n(dict hora → índices)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    criticas = indice.horas_criticas_por_regiao(limiar)
    regioes = sorted(indice.regioes)
    for k, regiao in enumerate(regioes):
        periodos = IndiceEnergia.agrupar_periodos(criticas[regiao])
        ax3.broken_barh([(i, j - i + 1) for i, j in periodos], (k - 0.35, 0.7), color=COR_CRITICO)
    ax3.set_yticks(range(len(regioes)))
    ax3.set_yticklabels(regioes)
    ax3.set_xlabel("data")
    ax3.set_title(f"(c) Períodos críticos por região (utilização ≥ {limiar:.0%})\n(set de horas → períodos contínuos)")
    ax3.set_xlim(0, len(indice.serie))
    ax3.grid(alpha=0.3, axis="x")
    _rotulos_de_dia(ax3, indice, 96)
    fig.suptitle("Figura 4 — Consultas da Parte A sobre as estruturas de dados")
    fig.tight_layout()
    _salvar(fig, salvar_em)
    return fig
