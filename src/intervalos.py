"""Tipo comum aos algoritmos de intervalo crítico (Partes B e C da Questão 2)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ResultadoIntervalo:
    """Intervalo contínuo ``[inicio, fim]`` (índices inclusivos) de maior soma.

    Critério de desempate, idêntico nos três algoritmos (para que possam ser
    comparados por igualdade): maior soma; depois o intervalo mais curto;
    depois o que começa mais cedo.
    """

    inicio: int
    fim: int
    soma: int
    operacoes: int  # nº de somas/comparações relevantes executadas
    profundidade: int = 0  # profundidade máxima da recursão (só D&C)

    @property
    def tamanho(self) -> int:
        return self.fim - self.inicio + 1


def chave_desempate(soma: int, inicio: int, fim: int) -> tuple[int, int, int]:
    """Chave de comparação: quanto MAIOR, melhor (soma, mais curto, mais cedo)."""
    return (soma, -(fim - inicio), -inicio)


def validar_serie(serie: Sequence[int]) -> None:
    if len(serie) == 0:
        raise ValueError("a série não pode ser vazia")
