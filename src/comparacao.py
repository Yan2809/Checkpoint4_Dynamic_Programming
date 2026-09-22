"""Parte D — Comparação Greedy x Programação Dinâmica.

Três investigações sobre os mesmos dados:

1. ``comparar_capacidades``  varre a capacidade do veículo na instância principal;
2. ``estatisticas_por_seed`` repete o teste em muitas instâncias sorteadas;
3. ``contraexemplo_proprio`` instância mínima construída à mão em que o guloso NÃO é ótimo.
"""
from __future__ import annotations

from dataclasses import dataclass

from .dynamic_programming import preencher_tabela, programacao_dinamica_atendimento
from .estruturas import CENTRO, RECURSOS, GrafoLogistico, Instancia, Ponto, Solucao
from .gerador_q1 import gerar_instancia
from .greedy import LAMBDA_PADRAO, guloso_atendimento
from .grafos import TabelaDistancias, pontos_alcancaveis


@dataclass(frozen=True)
class LinhaComparacao:
    capacidade: int
    beneficio_guloso: int
    beneficio_dp: int

    @property
    def diferenca(self) -> int:
        return self.beneficio_dp - self.beneficio_guloso

    @property
    def guloso_otimo(self) -> bool:
        return self.diferenca == 0


def comparar_capacidades(grafo: GrafoLogistico, capacidades: list[int],
                         lam: float = LAMBDA_PADRAO) -> list[LinhaComparacao]:
    """Benefício de cada método para cada capacidade.

    Truque da DP: a última linha DP[N][c] já contém o ótimo de *todas* as
    capacidades c <= C_max, então uma única tabela responde a todas as
    capacidades (custo Θ(N·C_max) uma vez, em vez de uma DP por capacidade).
    O guloso, por depender da capacidade, é executado uma vez por valor.
    """
    if not capacidades:
        return []
    tabela_dist = TabelaDistancias(grafo)
    candidatas = pontos_alcancaveis(grafo)
    pesos = [grafo.ponto(j).carga_kg for j in candidatas]
    beneficios = [grafo.ponto(j).beneficio for j in candidatas]
    tabela_dp = preencher_tabela(pesos, beneficios, max(capacidades))

    linhas = []
    for c in capacidades:
        guloso = guloso_atendimento(grafo, c, tabela_dist, candidatas, lam)
        linhas.append(LinhaComparacao(c, guloso.beneficio, tabela_dp[-1][c]))
    return linhas


def estatisticas_por_seed(seeds: range | list[int], lam: float = LAMBDA_PADRAO,
                          **parametros_gerador) -> dict:
    """Em quantas instâncias sorteadas o guloso é ótimo? Qual a perda média/máxima?"""
    n_otimo = 0
    perdas_pct: list[float] = []
    pior: tuple[float, int] = (0.0, -1)
    for seed in seeds:
        inst = gerar_instancia(seed, **parametros_gerador)
        tabela_dist = TabelaDistancias(inst.grafo)
        guloso = guloso_atendimento(inst.grafo, inst.capacidade, tabela_dist, lam=lam)
        dp, _ = programacao_dinamica_atendimento(inst.grafo, inst.capacidade, tabela_dist)
        perda = 100.0 * (dp.beneficio - guloso.beneficio) / dp.beneficio if dp.beneficio else 0.0
        perdas_pct.append(perda)
        n_otimo += guloso.beneficio == dp.beneficio
        pior = max(pior, (perda, seed))
    total = len(perdas_pct)
    return {
        "instancias": total,
        "guloso_otimo": n_otimo,
        "guloso_subotimo": total - n_otimo,
        "perda_media_pct": sum(perdas_pct) / total if total else 0.0,
        "perda_maxima_pct": pior[0],
        "seed_pior_caso": pior[1],
    }


def contraexemplo_proprio() -> Instancia:
    """Instância mínima em que o guloso falha (todas as vias medem 1 km; as
    coordenadas são só um layout ilustrativo para as figuras).

    Capacidade = 10 kg. Regiões (carga em kg, benefício):
        A: 6 kg, 60  -> razão 10,0 (a maior)
        B: 5 kg, 45  -> razão  9,0
        C: 5 kg, 45  -> razão  9,0
    """
    g = GrafoLogistico()
    g.adicionar_ponto(Ponto(CENTRO, "Centro", 0.0, 0.0, 0, 0, (0,) * len(RECURSOS), 0))
    # demanda só em "medicamentos" (1 kg/unidade) => carga_kg = nº de unidades
    med = RECURSOS.index("medicamentos")

    def demanda(kg: int) -> tuple[int, ...]:
        d = [0] * len(RECURSOS)
        d[med] = kg
        return tuple(d)

    g.adicionar_ponto(Ponto(1, "A", -30.0, 30.0, 100, 3, demanda(6), 60))
    g.adicionar_ponto(Ponto(2, "B", 30.0, 30.0, 90, 3, demanda(5), 45))
    g.adicionar_ponto(Ponto(3, "C", 0.0, -45.0, 90, 3, demanda(5), 45))
    for u, v in [(0, 1), (0, 2), (0, 3), (1, 2), (2, 3), (1, 3)]:
        g.adicionar_aresta(u, v, 1.0)
    return Instancia(g, 10, seed=None)


def analisar_contraexemplo(lam: float = LAMBDA_PADRAO) -> dict:
    """Roda guloso e DP no contraexemplo e devolve soluções + explicação textual."""
    inst = contraexemplo_proprio()
    tabela_dist = TabelaDistancias(inst.grafo)
    guloso = guloso_atendimento(inst.grafo, inst.capacidade, tabela_dist, lam=lam)
    dp, resultado = programacao_dinamica_atendimento(inst.grafo, inst.capacidade, tabela_dist)
    explicacao = (
        f"Com capacidade {inst.capacidade} kg, o guloso escolhe primeiro A "
        f"(score {60 / (6 + lam):.2f} > {45 / (5 + lam):.2f} de B e C) e sobram 4 kg, "
        f"insuficientes para B ou C (5 kg cada): benefício {guloso.beneficio}. "
        f"A DP percebe que B + C ocupam exatamente 10 kg e valem {dp.beneficio}. "
        "O guloso otimiza a razão benefício/kg 'agora', mas a indivisibilidade dos "
        "atendimentos faz o item de maior razão fragmentar a capacidade e deixar "
        "um resto inaproveitável; a DP compara todas as combinações via DP[i][c]."
    )
    return {"instancia": inst, "guloso": guloso, "dp": dp, "resultado_dp": resultado,
            "explicacao": explicacao}


def descrever(solucao: Solucao) -> str:
    """Resumo de uma linha de uma solução (para logs e relatórios)."""
    ordem = " -> ".join(f"P{j:02d}" for j in solucao.ordem) or "(vazio)"
    return (f"{solucao.nome}: benefício={solucao.beneficio}, carga={solucao.carga} kg, "
            f"rota={solucao.distancia:.1f} km, atendidos={len(solucao.ordem)} [{ordem}]")
