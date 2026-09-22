"""Parte C — Programação Dinâmica (mochila 0/1) para escolher os atendimentos.

FORMULAÇÃO

Sejam as N regiões candidatas numeradas 1..N, com carga w_i (kg, inteiro > 0)
e benefício b_i. Seja C a capacidade do veículo (kg, inteiro).

1. ESTADO      DP[i][c] = maior benefício total possível considerando apenas
               as i primeiras regiões, com capacidade disponível de c kg.
2. DECISÃO     para a região i: NÃO atender (herda DP[i-1][c]) ou atender
               (ganha b_i e consome w_i kg de capacidade).
3. CASO-BASE   DP[0][c] = 0 para todo c (nenhuma região => benefício 0).
               (DP[i][0] = 0 segue da recorrência, pois w_i >= 1.)
4. RECORRÊNCIA DP[i][c] = DP[i-1][c]                              se w_i > c
               DP[i][c] = max( DP[i-1][c], DP[i-1][c-w_i] + b_i )  se w_i <= c
5. RECONSTRUÇÃO partindo de (i=N, c=C) e subindo: se DP[i][c] != DP[i-1][c]
               a região i foi atendida (só assim o valor poderia ter
               crescido); então c <- c - w_i. Caso contrário, i foi ignorada.
               Em empate escolhe-se NÃO atender (solução com menos regiões).

Por que é ótimo: subestrutura ótima (a melhor solução para (i, c) contém
uma melhor solução para (i-1, c) ou (i-1, c-w_i)) e subproblemas
sobrepostos (o mesmo (i, c) é reutilizado por vários estados maiores).

COMPLEXIDADE: N·(C+1) células, cada uma em O(1) => tempo Θ(N·C); espaço Θ(N·C)
com a tabela completa (necessária para reconstruir) ou Θ(C) se só o valor
ótimo interessa (``melhor_valor_1d``). É pseudopolinomial: depende do valor
de C, não do número de bits para escrevê-lo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .estruturas import GrafoLogistico, Solucao
from .grafos import TabelaDistancias, montar_solucao, ordenar_vizinho_mais_proximo, pontos_alcancaveis


@dataclass(frozen=True)
class ResultadoDP:
    """Tudo o que as visualizações precisam saber sobre uma execução da DP."""

    tabela: list[list[int]]  # tabela[i][c], i = 0..N, c = 0..C
    candidatas: list[int]  # ids na ordem usada (candidatas[i-1] é a região i)
    pesos: list[int]
    beneficios: list[int]
    escolhidos: list[int]  # índices 0-based em ``candidatas``
    capacidade: int

    @property
    def beneficio_otimo(self) -> int:
        return self.tabela[-1][self.capacidade]


def _validar(pesos: Sequence[int], beneficios: Sequence[int], capacidade: int) -> None:
    if len(pesos) != len(beneficios):
        raise ValueError("pesos e benefícios devem ter o mesmo tamanho")
    if not isinstance(capacidade, int) or capacidade < 0:
        raise ValueError("capacidade deve ser um inteiro >= 0")
    if any(not isinstance(w, int) or w <= 0 for w in pesos):
        raise ValueError("pesos devem ser inteiros positivos")
    if any(b < 0 for b in beneficios):
        raise ValueError("benefícios não podem ser negativos")


def preencher_tabela(pesos: Sequence[int], beneficios: Sequence[int],
                     capacidade: int) -> list[list[int]]:
    """Preenche DP[0..N][0..C] linha a linha (ver recorrência no docstring do módulo)."""
    _validar(pesos, beneficios, capacidade)
    n = len(pesos)
    tabela = [[0] * (capacidade + 1) for _ in range(n + 1)]  # linha 0 = caso-base
    for i in range(1, n + 1):
        w, b = pesos[i - 1], beneficios[i - 1]
        anterior, atual = tabela[i - 1], tabela[i]
        for c in range(capacidade + 1):
            atual[c] = anterior[c]  # decisão 1: não atender
            if w <= c and anterior[c - w] + b > atual[c]:  # decisão 2: atender
                atual[c] = anterior[c - w] + b
    return tabela


def reconstruir(tabela: list[list[int]], pesos: Sequence[int], capacidade: int) -> list[int]:
    """Índices (0-based, crescentes) das regiões atendidas na solução ótima. O(N)."""
    escolhidos: list[int] = []
    c = capacidade
    for i in range(len(pesos), 0, -1):
        if tabela[i][c] != tabela[i - 1][c]:  # o valor só sobe se a região i foi atendida
            escolhidos.append(i - 1)
            c -= pesos[i - 1]
    escolhidos.reverse()
    return escolhidos


def melhor_valor_1d(pesos: Sequence[int], beneficios: Sequence[int], capacidade: int) -> int:
    """Só o valor ótimo, em O(C) de memória (uma única linha reaproveitada).

    A linha é percorrida de c = C até w (decrescente) para que DP[c - w] ainda
    seja o valor da linha *anterior*; em ordem crescente, a mesma região
    poderia ser usada várias vezes (mochila ilimitada).
    """
    _validar(pesos, beneficios, capacidade)
    linha = [0] * (capacidade + 1)
    for w, b in zip(pesos, beneficios):
        for c in range(capacidade, w - 1, -1):
            if linha[c - w] + b > linha[c]:
                linha[c] = linha[c - w] + b
    return linha[capacidade]


def programacao_dinamica_atendimento(grafo: GrafoLogistico, capacidade: int,
                                     tabela_dist: TabelaDistancias,
                                     candidatas: list[int] | None = None
                                     ) -> tuple[Solucao, ResultadoDP]:
    """Escolhe o conjunto ótimo de regiões e o ordena por vizinho mais próximo."""
    if candidatas is None:
        candidatas = pontos_alcancaveis(grafo)
    candidatas = sorted(candidatas)
    pesos = [grafo.ponto(j).carga_kg for j in candidatas]
    beneficios = [grafo.ponto(j).beneficio for j in candidatas]

    tabela = preencher_tabela(pesos, beneficios, capacidade)
    idx = reconstruir(tabela, pesos, capacidade)
    ordem = ordenar_vizinho_mais_proximo([candidatas[i] for i in idx], tabela_dist)

    resultado = ResultadoDP(tabela, candidatas, pesos, beneficios, idx, capacidade)
    return montar_solucao("Programação Dinâmica", ordem, grafo, tabela_dist), resultado
