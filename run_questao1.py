"""Executa a Questão 1 de ponta a ponta: dados -> guloso -> DP -> comparação -> figuras.

Uso:
    python run_questao1.py                # usa a SEED_GRUPO de src/gerador_q1.py
    python run_questao1.py --seed 7 --lambda 0.5
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")  # gera PNGs sem abrir janelas

from src.comparacao import (analisar_contraexemplo, comparar_capacidades, descrever,
                            estatisticas_por_seed)
from src.dynamic_programming import programacao_dinamica_atendimento
from src.gerador_q1 import SEED_GRUPO, gerar_instancia
from src.greedy import LAMBDA_PADRAO, guloso_atendimento
from src.grafos import TabelaDistancias
from src.io_dados import salvar_instancia
from src.visualizacao_q1 import figura_dp, figura_greedy_vs_dp, figura_grafo, figura_solucoes

RAIZ = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=SEED_GRUPO, help="seed do grupo")
    ap.add_argument("--lambda", dest="lam", type=float, default=LAMBDA_PADRAO,
                    help="peso da distância no score guloso")
    args = ap.parse_args()

    pasta_fig = RAIZ / "figures" / "questao1"
    linhas: list[str] = []

    def log(texto: str = "") -> None:
        print(texto)
        linhas.append(texto)

    # --- Parte A: dados -------------------------------------------------
    inst = gerar_instancia(args.seed)
    g = inst.grafo
    salvar_instancia(inst, RAIZ / "data")
    carga_total = sum(p.carga_kg for p in g.pontos_atendimento())
    log(f"SEED = {args.seed} | λ = {args.lam}")
    log(f"Pontos: {len(g.pontos_atendimento())} | vértices (com CD): {g.num_vertices} | "
        f"vias: {g.num_arestas} ({g.num_arestas_disponiveis} disponíveis, "
        f"{g.num_arestas_bloqueadas} bloqueadas) | completo? {g.eh_completo()}")
    log(f"Carga total demandada: {carga_total} kg | capacidade do veículo: {inst.capacidade} kg")

    # --- Partes B e C: mesmos dados, mesma tabela de distâncias ----------
    tabela_dist = TabelaDistancias(g)
    guloso = guloso_atendimento(g, inst.capacidade, tabela_dist, lam=args.lam)
    dp, resultado = programacao_dinamica_atendimento(g, inst.capacidade, tabela_dist)
    log("\n== Solução principal ==")
    log(descrever(guloso))
    log(descrever(dp))
    log(f"Diferença (DP − guloso) = {dp.beneficio - guloso.beneficio} de benefício")

    # --- Parte D: comparação ------------------------------------------------
    passo = max(1, carga_total // 100)
    capacidades = sorted(set(range(0, carga_total + 1, passo)) | {carga_total, inst.capacidade})
    varredura = comparar_capacidades(g, capacidades, args.lam)
    n_iguais = sum(l.guloso_otimo for l in varredura)
    log(f"\n== Varredura de capacidade (0..{carga_total} kg, passo {passo}) ==")
    log(f"Guloso ótimo em {n_iguais}/{len(varredura)} capacidades; "
        f"maior perda absoluta = {max(l.diferenca for l in varredura)}")

    stats = estatisticas_por_seed(range(1, 201), args.lam)
    log("\n== 200 instâncias sorteadas (seeds 1..200, mesmo gerador) ==")
    log(f"Guloso ótimo em {stats['guloso_otimo']}/{stats['instancias']} | "
        f"perda média = {stats['perda_media_pct']:.2f}% | "
        f"pior caso = {stats['perda_maxima_pct']:.2f}% (seed {stats['seed_pior_caso']})")

    contra = analisar_contraexemplo(args.lam)
    log("\n== Contraexemplo próprio ==")
    log(descrever(contra["guloso"]))
    log(descrever(contra["dp"]))
    log(contra["explicacao"])

    # --- Parte E: figuras ---------------------------------------------------
    figura_grafo(g, pasta_fig / "fig1_grafo.png")
    figura_solucoes(g, [guloso, dp], tabela_dist, inst.capacidade,
                    "Figura 2 — Locais atendidos × não atendidos e sequência de atendimento",
                    pasta_fig / "fig2_solucao.png")
    figura_dp(resultado, pasta_fig / "fig3_programacao_dinamica.png")
    figura_greedy_vs_dp(varredura, inst.capacidade, pasta_fig / "fig4_guloso_vs_dp.png")
    ci = contra["instancia"]
    figura_solucoes(ci.grafo, [contra["guloso"], contra["dp"]], TabelaDistancias(ci.grafo),
                    ci.capacidade, "Figura 5 — Contraexemplo: guloso ≠ ótimo",
                    pasta_fig / "fig5_contraexemplo.png", rotulos_vias=True)
    log(f"\nFiguras salvas em {pasta_fig.relative_to(RAIZ)}")

    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs" / "resultados_questao1.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
