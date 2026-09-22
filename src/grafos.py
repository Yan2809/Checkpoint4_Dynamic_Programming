"""Algoritmos de grafo implementados pelo grupo (sem networkx).

* Dijkstra com ``heapq`` (min-heap) e "lazy deletion".
* BFS com ``collections.deque`` para descobrir quais pontos são alcançáveis.
* Funções auxiliares de rota (distância total, ordenação por vizinho mais próximo).
"""
from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Sequence

from .estruturas import CENTRO, GrafoLogistico, Solucao

INF = math.inf


def dijkstra(grafo: GrafoLogistico, origem: int) -> tuple[dict[int, float], dict[int, int]]:
    """Menores distâncias a partir de ``origem`` usando apenas vias disponíveis.

    Estrutura: min-heap de pares ``(distância_provisória, vértice)``. A
    operação dominante é "extrair o vértice mais próximo ainda não fechado":
    O(log V) no heap contra O(V) numa varredura linear.

    Lazy deletion: em vez de atualizar a chave de um vértice já no heap
    (o ``heapq`` não oferece decrease-key), insere-se uma nova entrada e as
    entradas velhas (``d > distancia[u]``) são descartadas ao sair do heap.

    Complexidade: cada via é relaxada no máximo 2 vezes (uma por extremidade)
    => até 2E inserções, cada uma O(log E) = O(log V)  =>  O(E log V) tempo e
    O(V + E) espaço.

    Retorna ``(distancia, anterior)``. Vértices inalcançáveis ficam com ``inf``.
    """
    if not grafo.tem_ponto(origem):
        raise ValueError(f"origem {origem} não existe no grafo")
    distancia = {v: INF for v in grafo.vertices()}
    anterior: dict[int, int] = {}
    distancia[origem] = 0.0
    fila: list[tuple[float, int]] = [(0.0, origem)]
    while fila:
        d, u = heapq.heappop(fila)
        if d > distancia[u]:  # entrada obsoleta
            continue
        for v, peso in grafo.vizinhos(u).items():
            nova = d + peso
            if nova < distancia[v]:
                distancia[v] = nova
                anterior[v] = u
                heapq.heappush(fila, (nova, v))
    return distancia, anterior


def reconstruir_caminho(anterior: dict[int, int], origem: int, destino: int) -> list[int]:
    """Caminho ``origem -> destino`` a partir do dicionário de predecessores.

    Retorna lista vazia se ``destino`` for inalcançável.
    """
    if destino == origem:
        return [origem]
    if destino not in anterior:
        return []
    caminho = [destino]
    while caminho[-1] != origem:
        caminho.append(anterior[caminho[-1]])
    caminho.reverse()
    return caminho


class TabelaDistancias:
    """Cache de Dijkstra por origem.

    O guloso consulta a distância entre a posição atual e *todos* os pontos
    pendentes a cada passo; sem cache, o mesmo Dijkstra seria repetido. Cada
    origem é calculada uma única vez: O(E log V) por origem distinta.

    Atenção: se o grafo for alterado (via bloqueada/liberada) depois da
    criação, crie uma nova tabela.
    """

    def __init__(self, grafo: GrafoLogistico) -> None:
        self._grafo = grafo
        self._cache: dict[int, tuple[dict[int, float], dict[int, int]]] = {}

    def _resultado(self, origem: int) -> tuple[dict[int, float], dict[int, int]]:
        if origem not in self._cache:
            self._cache[origem] = dijkstra(self._grafo, origem)
        return self._cache[origem]

    def distancia(self, origem: int, destino: int) -> float:
        return self._resultado(origem)[0][destino]

    def caminho(self, origem: int, destino: int) -> list[int]:
        return reconstruir_caminho(self._resultado(origem)[1], origem, destino)

    @property
    def origens_calculadas(self) -> int:
        return len(self._cache)


def pontos_alcancaveis(grafo: GrafoLogistico, origem: int = CENTRO) -> list[int]:
    """Ids dos pontos de atendimento acessíveis a partir do centro (BFS, O(V+E)).

    ``deque`` porque a BFS remove sempre do início da fila: ``popleft`` é O(1),
    enquanto ``list.pop(0)`` é O(n).
    """
    visto = {origem}
    fila = deque([origem])
    while fila:
        u = fila.popleft()
        for v in grafo.vizinhos(u):
            if v not in visto:
                visto.add(v)
                fila.append(v)
    return sorted(v for v in visto if v != CENTRO)


def distancia_da_rota(ordem: Sequence[int], tabela: TabelaDistancias,
                      origem: int = CENTRO, retornar: bool = True) -> float:
    """Distância percorrida em ``origem -> ordem[0] -> ... -> ordem[-1] (-> origem)``."""
    total = 0.0
    atual = origem
    for destino in ordem:
        total += tabela.distancia(atual, destino)
        atual = destino
    if retornar and ordem:
        total += tabela.distancia(atual, origem)
    return total


def ordenar_vizinho_mais_proximo(selecionados: Sequence[int], tabela: TabelaDistancias,
                                 origem: int = CENTRO) -> list[int]:
    """Ordena um conjunto já escolhido pelo critério do vizinho mais próximo.

    A DP escolhe *quais* pontos atender; a ordem da visita é um problema de
    caixeiro-viajante (NP-difícil), tratado aqui por heurística O(K^2).
    """
    pendentes = set(selecionados)
    atual = origem
    ordem: list[int] = []
    while pendentes:
        proximo = min(pendentes, key=lambda j: (tabela.distancia(atual, j), j))
        ordem.append(proximo)
        pendentes.remove(proximo)
        atual = proximo
    return ordem


def montar_solucao(nome: str, ordem: Sequence[int], grafo: GrafoLogistico,
                   tabela: TabelaDistancias) -> Solucao:
    """Consolida uma ordem de atendimento em um objeto ``Solucao``."""
    atendidos = [grafo.ponto(j) for j in ordem]
    todos = {p.id for p in grafo.pontos_atendimento()}
    return Solucao(
        nome=nome,
        ordem=tuple(ordem),
        beneficio=sum(p.beneficio for p in atendidos),
        carga=sum(p.carga_kg for p in atendidos),
        distancia=distancia_da_rota(ordem, tabela),
        nao_atendidos=tuple(sorted(todos - set(ordem))),
    )
