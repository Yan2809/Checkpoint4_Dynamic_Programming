"""Parte D — Experimento de escalabilidade (Força Bruta x Dividir e Conquistar).

Para cada tamanho n:
* gera-se uma série de n horas com o MESMO gerador da Parte A (``gerar_registros``),
  reduzida a criticidade horária (mesmo pipeline dos dados reais);
* mede-se o tempo médio de ``repeticoes`` execuções (``time.perf_counter``);
* registra-se o nº de operações relevantes contado pelo próprio algoritmo;
* mede-se o pico de memória Python com ``tracemalloc`` em uma execução separada
  (o tracemalloc distorce o tempo, por isso não é usado durante a medição de tempo).

A força bruta cúbica só é executada até ``LIMITE_CUBICO`` (Θ(n³) explode).
"""
from __future__ import annotations

import math
import random
import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable, Sequence

from .brute_force import forca_bruta_cubica, forca_bruta_quadratica
from .config import SEED_GRUPO
from .divide_conquer import dividir_e_conquistar
from .estruturas_energia import serie_horaria
from .gerador_q2 import gerar_registros
from .intervalos import ResultadoIntervalo

TAMANHOS_PADRAO = (100, 250, 500, 1000, 2000, 5000)
LIMITE_CUBICO = 500

ALGORITMOS: dict[str, Callable[[Sequence[int]], ResultadoIntervalo]] = {
    "Força bruta O(n³)": forca_bruta_cubica,
    "Força bruta O(n²)": forca_bruta_quadratica,
    "Dividir e Conquistar": dividir_e_conquistar,
}


@dataclass(frozen=True)
class LinhaEscalabilidade:
    algoritmo: str
    n: int
    tempo_s: float
    operacoes: int
    memoria_pico_kib: float
    soma: int  # soma encontrada (todos os algoritmos devem concordar)


def gerar_serie(n: int, seed: int = SEED_GRUPO) -> list[int]:
    """Série de criticidade horária com exatamente n pontos, via gerador da Parte A."""
    registros = gerar_registros(seed, n_horas=n)
    return [p.criticidade for p in serie_horaria(registros)]


def serie_sintetica(n: int, seed: int = SEED_GRUPO) -> list[int]:
    """Série aleatória (média negativa, como a real) para n muito grande, sem gerar registros."""
    rng = random.Random(seed)
    return [round(rng.gauss(-8000, 25000)) for _ in range(n)]


def medir_tempo(algoritmo: Callable, serie: Sequence[int], repeticoes: int) -> tuple[float, ResultadoIntervalo]:
    """Tempo médio (s) de ``repeticoes`` execuções e o último resultado."""
    total, resultado = 0.0, None
    for _ in range(repeticoes):
        t0 = time.perf_counter()
        resultado = algoritmo(serie)
        total += time.perf_counter() - t0
    return total / repeticoes, resultado


def medir_memoria_kib(algoritmo: Callable, serie: Sequence[int]) -> float:
    """Pico de memória (KiB) alocada DURANTE a execução (a série de entrada não conta)."""
    tracemalloc.start()
    try:
        algoritmo(serie)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return pico / 1024


def _repeticoes(nome: str, n: int) -> int:
    custo = n ** 3 if "O(n³)" in nome else n ** 2 if "O(n²)" in nome else n * 20
    return 1 if custo > 5e7 else 3 if custo > 5e6 else 5


def executar_experimento(tamanhos: Sequence[int] = TAMANHOS_PADRAO, seed: int = SEED_GRUPO,
                         repeticoes: int | None = None) -> list[LinhaEscalabilidade]:
    """Roda todos os algoritmos em todos os tamanhos (cúbica limitada a LIMITE_CUBICO)."""
    if not tamanhos or any(n < 1 for n in tamanhos):
        raise ValueError("tamanhos deve ser uma lista de inteiros positivos")
    linhas: list[LinhaEscalabilidade] = []
    for n in tamanhos:
        serie = gerar_serie(n, seed)
        somas = set()
        for nome, algoritmo in ALGORITMOS.items():
            if "O(n³)" in nome and n > LIMITE_CUBICO:
                continue
            reps = repeticoes if repeticoes is not None else _repeticoes(nome, n)
            tempo, resultado = medir_tempo(algoritmo, serie, reps)
            memoria = medir_memoria_kib(algoritmo, serie)
            somas.add(resultado.soma)
            linhas.append(LinhaEscalabilidade(nome, n, tempo, resultado.operacoes, memoria,
                                              resultado.soma))
        if len(somas) != 1:
            raise RuntimeError(f"algoritmos discordam para n={n}: {somas}")
    return linhas


def estimar_expoente(ns: Sequence[float], tempos: Sequence[float]) -> float:
    """Inclinação da reta log(tempo) x log(n) (mínimos quadrados): T ≈ c · n^expoente."""
    if len(ns) != len(tempos) or len(ns) < 2:
        raise ValueError("são necessários pelo menos 2 pontos")
    xs = [math.log(n) for n in ns]
    ys = [math.log(t) for t in tempos]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        raise ValueError("tamanhos devem ser distintos")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def extrapolar(tempo_ref: float, n_ref: int, n_alvo: int, expoente: float) -> float:
    """Tempo esperado em ``n_alvo`` supondo T proporcional a n^expoente."""
    return tempo_ref * (n_alvo / n_ref) ** expoente


def experimento_viabilidade(n_alvo: int = 1_000_000, seed: int = SEED_GRUPO) -> dict:
    """Responde 'e se forem 1.000.000 de registros?': mede o D&C e extrapola a força bruta.

    A força bruta quadrática NÃO é executada em n_alvo (levaria dias): usa-se o tempo
    medido em n=5000 e o expoente 2. O D&C é medido de fato.
    """
    ref_n = 5000
    serie_ref = gerar_serie(ref_n, seed)
    t_bruta_ref, _ = medir_tempo(forca_bruta_quadratica, serie_ref, 1)
    serie_grande = serie_sintetica(n_alvo, seed)
    t_dc, res = medir_tempo(dividir_e_conquistar, serie_grande, 1)
    return {
        "n_alvo": n_alvo,
        "tempo_dc_s": t_dc,
        "operacoes_dc": res.operacoes,
        "profundidade_dc": res.profundidade,
        "tempo_bruta_ref_s": t_bruta_ref,
        "n_ref": ref_n,
        "tempo_bruta_extrapolado_s": extrapolar(t_bruta_ref, ref_n, n_alvo, 2.0),
        "operacoes_bruta": n_alvo * (n_alvo + 1) // 2,
    }
