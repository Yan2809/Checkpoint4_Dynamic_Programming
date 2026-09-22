"""Executa a Questão 2 de ponta a ponta: dados -> estruturas -> força bruta -> D&C -> escalabilidade -> figuras.

Uso:
    python run_questao2.py                 # SEED_GRUPO de src/config.py
    python run_questao2.py --seed 7
    python run_questao2.py --rapido        # tamanhos menores, sem o teste de 1.000.000 (poucos segundos)
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from src.brute_force import forca_bruta_cubica, forca_bruta_quadratica
from src.config import SEED_GRUPO
from src.divide_conquer import dividir_e_conquistar
from src.escalabilidade import (ALGORITMOS, TAMANHOS_PADRAO, estimar_expoente, executar_experimento,
                                experimento_viabilidade)
from src.estruturas_energia import ESCALA, IndiceEnergia
from src.gerador_q2 import gerar_registros, salvar_registros
from src.visualizacao_q2 import (figura_divide_conquer, figura_escalabilidade, figura_estruturas,
                                 figura_serie_temporal)

RAIZ = Path(__file__).resolve().parent
N_HORAS, UNIDADES = 720, 2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=SEED_GRUPO)
    ap.add_argument("--rapido", action="store_true")
    args = ap.parse_args()
    linhas: list[str] = []

    def log(texto: str = "") -> None:
        print(texto)
        linhas.append(texto)

    # --- Parte A ------------------------------------------------------------
    registros = gerar_registros(args.seed, N_HORAS, UNIDADES)
    salvar_registros(registros, RAIZ / "data", args.seed,
                     {"n_horas": N_HORAS, "unidades_por_regiao": UNIDADES, "inicio": "2026-01-01 00:00"})
    ix = IndiceEnergia(registros)
    serie = ix.serie_criticidade()
    log(f"SEED = {args.seed} | registros = {len(registros)} | horas = {len(serie)} | regiões = {sorted(ix.regioes)}")
    log("Consumo total por região (MWh): " +
        ", ".join(f"{r}={v:,.0f}" for r, v in ix.consumo_total_por_regiao().items()))
    perfil = ix.perfil_horario()
    hora_pico = max(perfil, key=perfil.get)
    log(f"Hora do dia de maior consumo médio: {hora_pico}h ({perfil[hora_pico]:.1f} MWh/unidade)")
    log("Top-3 picos do sistema (heap): " +
        "; ".join(f"{p.timestamp:%d/%m %Hh}={p.consumo:.0f} MWh" for p in ix.top_picos(3)))
    criticas = ix.horas_criticas_por_regiao(0.90)
    log("Horas com utilização ≥ 90% por região (set): " + ", ".join(f"{r}={len(h)}" for r, h in sorted(criticas.items())))
    comuns = ix.horas_criticas_em_comum(["Sudeste", "Sul"], 0.90)
    log(f"Horas críticas simultâneas Sudeste ∩ Sul: {len(comuns)}")
    i, j = ix.indices_do_intervalo(datetime(2026, 1, 10), datetime(2026, 1, 12, 23))
    log(f"Seleção 10/01–12/01 (bisect): horas {i}..{j}; criticidade somada (prefixos, O(1)) = {ix.soma_criticidade(i, j) / ESCALA:,.0f}")
    log(f"Horas com criticidade > 0: {sum(v > 0 for v in serie)} de {len(serie)}")

    # --- Partes B e C: mesmo dado, três algoritmos ------------------------------
    log("\n== Intervalo crítico (maior criticidade acumulada contínua) ==")
    resultados = {}
    for nome, alg in ALGORITMOS.items():
        t0 = time.perf_counter()
        resultados[nome] = alg(serie)
        dt = time.perf_counter() - t0
        r = resultados[nome]
        log(f"{nome:22}: [{r.inicio}, {r.fim}] ({ix.timestamps[r.inicio]:%d/%m %Hh} → {ix.timestamps[r.fim]:%d/%m %Hh}) "
            f"Σ={r.soma / ESCALA:,.2f} | operações={r.operacoes:,} | {dt * 1000:.1f} ms")
    assert len({(r.inicio, r.fim, r.soma) for r in resultados.values()}) == 1, "algoritmos discordam!"
    log("Os três algoritmos retornam o MESMO intervalo (ver testes).")
    trace: list = []
    dc = dividir_e_conquistar(serie, trace)
    log(f"D&C: profundidade = {dc.profundidade} níveis; nós internos registrados = {len(trace)} (= n − 1 = {len(serie) - 1})")

    # --- Parte D --------------------------------------------------------------
    tamanhos = (100, 250, 500, 1000) if args.rapido else TAMANHOS_PADRAO
    exp = executar_experimento(tamanhos, args.seed)
    with open(RAIZ / "data" / "escalabilidade_q2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["algoritmo", "n", "tempo_s", "operacoes", "memoria_pico_kib", "soma"])
        for l in exp:
            w.writerow([l.algoritmo, l.n, f"{l.tempo_s:.6f}", l.operacoes, f"{l.memoria_pico_kib:.1f}", l.soma])
    log("\n== Escalabilidade ==")
    log(f"{'algoritmo':22} {'n':>6} {'tempo (ms)':>12} {'operações':>14} {'mem. pico (KiB)':>16}")
    for l in exp:
        log(f"{l.algoritmo:22} {l.n:>6} {l.tempo_s * 1000:>12.2f} {l.operacoes:>14,} {l.memoria_pico_kib:>16.1f}")
    for nome in ALGORITMOS:
        pts = [(l.n, l.tempo_s) for l in exp if l.algoritmo == nome]
        if len(pts) >= 2:
            log(f"Expoente estimado (regressão log-log) — {nome}: {estimar_expoente(*zip(*pts)):.2f}")
    if not args.rapido:
        v = experimento_viabilidade(1_000_000, args.seed)
        log(f"\n== Viabilidade: {v['n_alvo']:,} registros ==")
        log(f"D&C medido: {v['tempo_dc_s']:.2f} s ({v['operacoes_dc']:,} operações, profundidade {v['profundidade_dc']})")
        log(f"Força bruta O(n²): {v['operacoes_bruta']:,} somas; extrapolado de n={v['n_ref']} "
            f"({v['tempo_bruta_ref_s']:.2f} s) => {v['tempo_bruta_extrapolado_s']:,.0f} s "
            f"≈ {v['tempo_bruta_extrapolado_s'] / 3600:.1f} h")

    # --- Parte E --------------------------------------------------------------
    pasta = RAIZ / "figures" / "questao2"
    figura_serie_temporal(ix, dc, pasta / "fig1_serie_temporal.png")
    figura_divide_conquer(ix, trace, dc, 4, pasta / "fig2_divide_conquer.png")
    figura_escalabilidade(exp, pasta / "fig3_escalabilidade.png")
    figura_estruturas(ix, 0.90, pasta / "fig4_estruturas.png")
    log(f"\nFiguras salvas em {pasta.relative_to(RAIZ)}")
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs" / "resultados_questao2.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
