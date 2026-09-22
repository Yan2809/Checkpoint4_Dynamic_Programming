"""Geração reprodutível do conjunto de dados da Questão 1.

Processo (tudo derivado de ``random.Random(seed)``; mesma seed => mesmos dados):

1. Sorteia as coordenadas (km) do centro de distribuição e dos pontos.
2. Sorteia pessoas afetadas, prioridade (1-5) e a demanda mínima de cada
   recurso (proporcional ao nº de pessoas, com ruído).
3. Benefício esperado ~ pessoas x prioridade x ruído (atender mais gente e
   com mais urgência vale mais).
4. Constrói a malha viária: árvore geradora mínima (Prim, garante que todos
   os pontos são alcançáveis) + vias extras entre pares próximos.
5. Declara algumas vias extras como bloqueadas. Como a árvore nunca é
   bloqueada, o grafo *disponível* permanece conexo.
6. Capacidade do veículo = fração da carga total demandada.
"""
from __future__ import annotations

import math
import random

from .config import SEED_GRUPO  # noqa: F401  (reexportado para run_questao1 e notebook)
from .estruturas import CENTRO, RECURSOS, GrafoLogistico, Instancia, Ponto, chave_aresta


# Pessoas atendidas por 1 unidade de cada recurso (em média).
_PESSOAS_POR_UNIDADE = {
    "agua": 60, "medicamentos": 120, "alimentos": 80, "higiene": 100, "cobertores": 70,
}


def gerar_instancia(seed: int = SEED_GRUPO, n_pontos: int = 20, n_disponiveis: int = 40,
                    n_bloqueadas: int = 6, fracao_capacidade: float = 0.4) -> Instancia:
    """Gera uma instância completa (grafo + capacidade). Ver docstring do módulo."""
    _validar_parametros(n_pontos, n_disponiveis, n_bloqueadas, fracao_capacidade)
    rng = random.Random(seed)

    grafo = GrafoLogistico()
    grafo.adicionar_ponto(Ponto(CENTRO, "Centro de Distribuição", 50.0, 50.0, 0, 0,
                                (0,) * len(RECURSOS), 0))
    for i in range(1, n_pontos + 1):
        grafo.adicionar_ponto(_gerar_ponto(rng, i))

    arvore = _arvore_geradora_minima(grafo)
    n_extras = n_disponiveis - len(arvore) + n_bloqueadas
    extras = _escolher_vias_extras(rng, grafo, arvore, n_extras)
    bloqueadas = set(rng.sample(extras, n_bloqueadas))

    for u, v in arvore + extras:
        distancia = _distancia_viaria(rng, grafo, u, v)
        grafo.adicionar_aresta(u, v, distancia, disponivel=(u, v) not in bloqueadas)

    carga_total = sum(p.carga_kg for p in grafo.pontos_atendimento())
    capacidade = max(1, int(carga_total * fracao_capacidade))
    return Instancia(grafo, capacidade, seed)


def _validar_parametros(n_pontos: int, n_disponiveis: int, n_bloqueadas: int,
                        fracao: float) -> None:
    if n_pontos < 1:
        raise ValueError("n_pontos deve ser >= 1")
    if n_disponiveis < n_pontos:
        raise ValueError("n_disponiveis deve ser >= n_pontos (a árvore já usa n_pontos vias)")
    if n_bloqueadas < 0:
        raise ValueError("n_bloqueadas deve ser >= 0")
    v = n_pontos + 1
    if n_disponiveis + n_bloqueadas >= v * (v - 1) // 2:
        raise ValueError("o grafo não pode ser completamente conectado")
    if not 0 < fracao <= 1:
        raise ValueError("fracao_capacidade deve estar em (0, 1]")


def _gerar_ponto(rng: random.Random, id_: int) -> Ponto:
    pessoas = rng.randint(40, 500)
    prioridade = rng.choices([1, 2, 3, 4, 5], weights=[2, 3, 4, 3, 2])[0]
    demanda = tuple(
        max(1, math.ceil(pessoas * rng.uniform(0.6, 1.4) / _PESSOAS_POR_UNIDADE[r]))
        for r in RECURSOS
    )
    beneficio = max(1, round(pessoas * prioridade * rng.uniform(0.8, 1.2) / 10))
    return Ponto(id_, f"P{id_:02d}", round(rng.uniform(0, 100), 1), round(rng.uniform(0, 100), 1),
                 pessoas, prioridade, demanda, beneficio)


def _euclidiana(grafo: GrafoLogistico, u: int, v: int) -> float:
    a, b = grafo.ponto(u), grafo.ponto(v)
    return math.hypot(a.x - b.x, a.y - b.y)


def _distancia_viaria(rng: random.Random, grafo: GrafoLogistico, u: int, v: int) -> float:
    """Distância euclidiana x fator de sinuosidade da via (1.0 a 1.4)."""
    return max(0.1, round(_euclidiana(grafo, u, v) * rng.uniform(1.0, 1.4), 1))


def _arvore_geradora_minima(grafo: GrafoLogistico) -> list[tuple[int, int]]:
    """Prim O(V^2) sobre as distâncias euclidianas; devolve vias ``(u, v)`` com u < v."""
    vertices = grafo.vertices()
    na_arvore = {vertices[0]}
    melhor = {v: (_euclidiana(grafo, vertices[0], v), vertices[0]) for v in vertices[1:]}
    arvore: list[tuple[int, int]] = []
    while melhor:
        v = min(melhor, key=lambda x: melhor[x][0])
        _, pai = melhor.pop(v)
        na_arvore.add(v)
        arvore.append(chave_aresta(pai, v))
        for w in melhor:
            d = _euclidiana(grafo, v, w)
            if d < melhor[w][0]:
                melhor[w] = (d, v)
    return sorted(arvore)


def _escolher_vias_extras(rng: random.Random, grafo: GrafoLogistico,
                          arvore: list[tuple[int, int]], quantidade: int) -> list[tuple[int, int]]:
    """Sorteia vias extras entre os pares mais próximos que ainda não são vias."""
    usadas = set(arvore)
    vertices = grafo.vertices()
    candidatos = [
        (u, v) for i, u in enumerate(vertices) for v in vertices[i + 1:] if (u, v) not in usadas
    ]
    candidatos.sort(key=lambda par: _euclidiana(grafo, *par))
    piscina = candidatos[: 3 * quantidade]
    return sorted(rng.sample(piscina, quantidade))
