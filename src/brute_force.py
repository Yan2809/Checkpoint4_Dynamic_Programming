"""Parte B — Força bruta: examina EXPLICITAMENTE todos os intervalos contínuos.

Problema: dada a série de criticidade ``a[0..n-1]`` (com valores positivos e
negativos), achar ``i <= j`` que maximize ``a[i] + ... + a[j]``.

Há n(n+1)/2 intervalos ``[i, j]``. Duas versões:

* ``forca_bruta_cubica``     recalcula a soma de cada intervalo do zero:
                             Σ comprimento = n(n+1)(n+2)/6 somas  -> Θ(n³)
* ``forca_bruta_quadratica`` para um ``i`` fixo, a soma de ``[i, j]`` é a de
                             ``[i, j-1]`` mais ``a[j]`` (soma corrente): 1 soma
                             por intervalo -> n(n+1)/2 somas -> Θ(n²)

Espaço auxiliar: O(1) nas duas (só variáveis escalares).
"""
from __future__ import annotations

from typing import Sequence

from .intervalos import ResultadoIntervalo, chave_desempate, validar_serie


def forca_bruta_cubica(serie: Sequence[int]) -> ResultadoIntervalo:
    """Θ(n³): três laços aninhados (início, fim, soma do trecho)."""
    validar_serie(serie)
    n = len(serie)
    melhor = None
    melhor_chave = None
    operacoes = 0
    for i in range(n):  # início
        for j in range(i, n):  # fim
            soma = 0
            for k in range(i, j + 1):  # soma o trecho inteiro, do zero
                soma += serie[k]
                operacoes += 1
            chave = chave_desempate(soma, i, j)
            if melhor_chave is None or chave > melhor_chave:
                melhor_chave, melhor = chave, (i, j, soma)
    i, j, soma = melhor
    return ResultadoIntervalo(i, j, soma, operacoes)


def forca_bruta_quadratica(serie: Sequence[int]) -> ResultadoIntervalo:
    """Θ(n²): dois laços; a soma do intervalo é atualizada incrementalmente."""
    validar_serie(serie)
    n = len(serie)
    melhor = None
    melhor_chave = None
    operacoes = 0
    for i in range(n):
        soma = 0
        for j in range(i, n):
            soma += serie[j]  # [i, j] = [i, j-1] + a[j]
            operacoes += 1
            chave = chave_desempate(soma, i, j)
            if melhor_chave is None or chave > melhor_chave:
                melhor_chave, melhor = chave, (i, j, soma)
    i, j, soma = melhor
    return ResultadoIntervalo(i, j, soma, operacoes)
