"""Parte B — Estratégia gulosa para decidir a ordem de atendimento.

FUNÇÃO DE PRIORIDADE (escolha do grupo)

    score(j | posição atual) = benefício_j / ( carga_j + λ · d(posição, j) )

* ``benefício_j``  já combina pessoas afetadas x prioridade (ver gerador).
* ``carga_j``      kg da demanda mínima -> consome a capacidade do veículo.
* ``d(posição, j)`` menor distância (Dijkstra, só vias disponíveis) da posição
  atual até j. ``λ`` (km -> kg equivalentes) é o "preço" de se deslocar: gasto
  de combustível/tempo que reduz o que ainda se pode entregar.

POR QUE ISSO É LOCALMENTE VANTAJOSO

O denominador é o custo total, em unidades de capacidade, de *obter* o
benefício de j. O score é, portanto, "benefício por unidade de custo".
Com λ = 0 e itens divisíveis, este é exatamente o problema da mochila
fracionária, para o qual escolher pelo maior benefício/peso é ÓTIMO
(argumento de troca: se uma solução ótima usa x kg de um item de razão menor
enquanto sobra capacidade de um item de razão maior, trocar esses x kg
aumenta o benefício em x·(r_maior − r_menor) > 0, contradição).

Quando os itens são indivisíveis (0/1), o guloso deixa de ser ótimo: ele
otimiza a razão *agora* sem considerar que o item escolhido pode "fragmentar"
a capacidade restante, deixando um resto que nenhum outro ponto aproveita.
Esse é o contraexemplo construído em ``comparacao.py``.

COMPLEXIDADE (ver docs/analise_complexidade.md)

A cada passo varre-se o conjunto de pendentes (O(N)); há no máximo N passos
=> O(N²) para as decisões, mais O(K · E log V) dos Dijkstra por posição
visitada. Não se usa heap para os scores porque eles dependem da posição
atual: mudam a cada passo, e reconstruir o heap custaria O(N) de qualquer
forma, o mesmo da varredura.
"""
from __future__ import annotations

from .estruturas import CENTRO, GrafoLogistico, Solucao
from .grafos import TabelaDistancias, montar_solucao, pontos_alcancaveis

LAMBDA_PADRAO = 0.5  # 1 km de deslocamento "vale" 0,5 kg de capacidade


def razao_beneficio_custo(beneficio: float, carga: float, distancia: float,
                          lam: float = LAMBDA_PADRAO) -> float:
    """Score guloso: benefício por unidade de custo (carga + λ · distância)."""
    custo = carga + lam * distancia
    if custo <= 0:
        raise ValueError("custo deve ser positivo")
    return beneficio / custo


def guloso_atendimento(grafo: GrafoLogistico, capacidade: int, tabela: TabelaDistancias,
                       candidatas: list[int] | None = None, lam: float = LAMBDA_PADRAO,
                       historico: list[dict] | None = None) -> Solucao:
    """Constrói a ordem de atendimento escolhendo, a cada passo, o maior score viável.

    Args:
        grafo: rede logística.
        capacidade: capacidade do veículo (kg, inteiro >= 0).
        tabela: cache de distâncias mínimas (mesma usada pela DP).
        candidatas: ids elegíveis; por padrão, os alcançáveis a partir do centro.
        lam: peso da distância no score (λ >= 0).
        historico: se fornecida, recebe um dict por passo (para explicar/depurar).
    """
    if capacidade < 0:
        raise ValueError("capacidade deve ser >= 0")
    if lam < 0:
        raise ValueError("lam deve ser >= 0")
    if candidatas is None:
        candidatas = pontos_alcancaveis(grafo)

    pendentes = set(candidatas)
    restante = capacidade
    posicao = CENTRO
    ordem: list[int] = []

    while True:
        # Só permanecem pendentes os pontos que ainda cabem: como `restante`
        # só diminui, quem não cabe agora nunca mais caberá.
        pendentes = {j for j in pendentes if grafo.ponto(j).carga_kg <= restante}
        if not pendentes:
            break
        pontuados = []
        for j in pendentes:
            p = grafo.ponto(j)
            d = tabela.distancia(posicao, j)
            pontuados.append((razao_beneficio_custo(p.beneficio, p.carga_kg, d, lam), -d, -j, j))
        score, _, _, escolhido = max(pontuados)  # desempate: mais perto, depois menor id
        if historico is not None:
            historico.append({
                "passo": len(ordem) + 1, "posicao": posicao, "escolhido": escolhido,
                "score": score, "restante_antes": restante,
                "ranking": [(s, j) for s, _, _, j in sorted(pontuados, reverse=True)[:3]],
            })
        ordem.append(escolhido)
        restante -= grafo.ponto(escolhido).carga_kg
        posicao = escolhido
        pendentes.discard(escolhido)

    return montar_solucao("Guloso", ordem, grafo, tabela)
