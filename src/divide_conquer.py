"""Parte C — Dividir e Conquistar para o intervalo contínuo de maior criticidade.

    DIVIDE          mid = (lo + hi) // 2  -> metade esquerda [lo, mid], direita [mid+1, hi]
       ↓
    SOLVE LEFT      melhor intervalo inteiramente em [lo, mid]      (chamada recursiva)
       ↓
    SOLVE RIGHT     melhor intervalo inteiramente em [mid+1, hi]    (chamada recursiva)
       ↓
    SOLVE CROSSING  melhor intervalo que contém mid E mid+1         (laços lineares)
       ↓
    COMBINE         o melhor dos três candidatos

CASO-BASE: um único elemento (lo == hi): o melhor intervalo é ele mesmo (não vazio).

CASO QUE ATRAVESSA A DIVISÃO: todo intervalo que cruza o meio é a união de um
*sufixo* da metade esquerda (terminando em mid) com um *prefixo* da direita
(começando em mid+1). As duas escolhas são independentes, então basta o
melhor sufixo (varrendo de mid para a esquerda) e o melhor prefixo (de mid+1
para a direita): custo O(hi - lo + 1), sem testar todos os pares.

CORREÇÃO: todo intervalo ótimo está inteiramente à esquerda, inteiramente à
direita ou cruza o meio — os três casos são exaustivos.

COMPLEXIDADE: T(n) = 2 T(n/2) + Θ(n)  =>  Θ(n log n)  (n por nível x log n níveis).
Espaço: profundidade da recursão ⌈log2 n⌉ + 1 quadros, cada um O(1) (usa índices,
não fatias)  =>  O(log n) auxiliar.
"""
from __future__ import annotations

from typing import NamedTuple, Sequence

from .intervalos import ResultadoIntervalo, chave_desempate, validar_serie

Candidato = tuple[int, int, int]  # (soma, inicio, fim)


class NoRecursao(NamedTuple):
    """Registro de um nó interno da recursão (usado para desenhar a Figura 2)."""

    nivel: int
    lo: int
    hi: int
    mid: int
    esquerda: Candidato
    direita: Candidato
    cruzado: Candidato
    melhor: Candidato


def _melhor_de(*candidatos: Candidato) -> Candidato:
    """COMBINE: candidato de maior chave (soma, mais curto, mais cedo)."""
    return max(candidatos, key=lambda c: chave_desempate(c[0], c[1], c[2]))


def _caso_cruzado(serie: Sequence[int], lo: int, mid: int, hi: int,
                  contador: list[int]) -> Candidato:
    """SOLVE CROSSING: melhor sufixo de [lo, mid] + melhor prefixo de [mid+1, hi]."""
    soma, melhor_esq, ini = 0, None, mid
    for i in range(mid, lo - 1, -1):  # cresce para a esquerda a partir do meio
        soma += serie[i]
        contador[0] += 1
        if melhor_esq is None or soma > melhor_esq:  # ">" estrito: mantém o mais curto
            melhor_esq, ini = soma, i
    soma, melhor_dir, fim = 0, None, mid + 1
    for j in range(mid + 1, hi + 1):  # cresce para a direita a partir do meio
        soma += serie[j]
        contador[0] += 1
        if melhor_dir is None or soma > melhor_dir:
            melhor_dir, fim = soma, j
    return (melhor_esq + melhor_dir, ini, fim)


def _resolver(serie: Sequence[int], lo: int, hi: int, nivel: int, contador: list[int],
              trace: list[NoRecursao] | None) -> Candidato:
    contador[1] = max(contador[1], nivel)
    if lo == hi:  # CASO-BASE
        contador[0] += 1
        return (serie[lo], lo, lo)
    mid = (lo + hi) // 2  # DIVIDE
    esquerda = _resolver(serie, lo, mid, nivel + 1, contador, trace)  # SOLVE LEFT
    direita = _resolver(serie, mid + 1, hi, nivel + 1, contador, trace)  # SOLVE RIGHT
    cruzado = _caso_cruzado(serie, lo, mid, hi, contador)  # SOLVE CROSSING
    melhor = _melhor_de(esquerda, direita, cruzado)  # COMBINE
    if trace is not None:
        trace.append(NoRecursao(nivel, lo, hi, mid, esquerda, direita, cruzado, melhor))
    return melhor


def dividir_e_conquistar(serie: Sequence[int],
                         trace: list[NoRecursao] | None = None) -> ResultadoIntervalo:
    """Intervalo contínuo de maior soma em Θ(n log n).

    Args:
        serie: criticidade por hora (inteiros; podem ser negativos).
        trace: se fornecida, recebe um ``NoRecursao`` por nó interno (para figuras/explicação).
    """
    validar_serie(serie)
    contador = [0, 0]  # [operações, nível máximo]
    soma, inicio, fim = _resolver(serie, 0, len(serie) - 1, 0, contador, trace)
    return ResultadoIntervalo(inicio, fim, soma, contador[0], contador[1] + 1)
