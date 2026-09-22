"""Estruturas de dados da Questão 2 (consumo de energia) — Parte A.

Cada estrutura foi escolhida por UMA operação em que oferece vantagem:

+----------------------------------+---------------------------------------------+---------------------+
| Estrutura                        | Operação em que é vantajosa                 | Custo               |
+----------------------------------+---------------------------------------------+---------------------+
| ``list[Registro]`` (ordenada)    | acesso por posição e *fatias contíguas*     | O(1) / O(k)         |
|                                  | (intervalos de tempo são índices contíguos) |                     |
| ``bisect`` sobre ``list`` de     | selecionar intervalo [t0, t1] por data      | O(log n)            |
| timestamps                       | (busca binária em vez de varrer tudo)       |                     |
| ``list`` de somas prefixo        | soma de criticidade de QUALQUER intervalo   | O(1) por consulta   |
| ``dict[str, list[int]]``         | consumo por região sem varrer os registros  | O(1) p/ achar a     |
|                                  | das outras regiões                          | região + O(k)       |
| ``dict[int, list[int]]``         | consumo por hora do dia (perfil diário)     | O(1) p/ achar a hora|
| ``tuple`` (``NamedTuple``)       | registro imutável e *hashable*: não é       | O(1)                |
|                                  | alterado por engano e pode ir em set/dict   |                     |
| ``set[int]``                     | "esta hora é crítica?" e interseção de      | O(1) / O(min(a,b))  |
|                                  | horas críticas entre regiões                |                     |
| ``heapq`` (min-heap de tamanho k)| os k maiores picos sem ordenar tudo         | O(n log k)          |
+----------------------------------+---------------------------------------------+---------------------+
"""
from __future__ import annotations

import bisect
import heapq
from collections import defaultdict
from datetime import datetime
from itertools import accumulate
from typing import Iterable, NamedTuple, Sequence

REGIOES = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")
PRIORIDADE_MIN, PRIORIDADE_MAX = 1, 5

# ---- parâmetros da função de criticidade (definição do grupo) -------------
U_REF = 0.80  # utilização de referência: acima disso a unidade "pesa" no sistema
PENALIDADE_EXCESSO = 3.0  # multiplicador extra quando consumo > capacidade
PESO_CUSTO = 10.0  # peso do prêmio de custo (preço acima do de referência)
CUSTO_REF = 300.0  # R$/MWh
ESCALA = 100  # criticidade em inteiros (centésimos): evita erro de ponto flutuante


class Registro(NamedTuple):
    """Uma medição horária de uma unidade consumidora (imutável)."""

    timestamp: datetime
    regiao: str
    unidade: str
    consumo: float  # MWh
    capacidade: float  # MWh disponíveis
    prioridade: int  # 1 (baixa) .. 5 (crítica: hospitais, etc.)
    custo: float  # R$/MWh


class PontoHorario(NamedTuple):
    """Agregado do sistema em uma hora."""

    timestamp: datetime
    consumo: float
    capacidade: float
    criticidade: int


class Pico(NamedTuple):
    consumo: float
    timestamp: datetime
    indice: int


def validar_registro(r: Registro) -> None:
    """Rejeita registros fisicamente impossíveis."""
    if r.consumo < 0:
        raise ValueError(f"consumo negativo: {r}")
    if r.capacidade <= 0:
        raise ValueError(f"capacidade deve ser positiva: {r}")
    if not PRIORIDADE_MIN <= r.prioridade <= PRIORIDADE_MAX:
        raise ValueError(f"prioridade fora de {PRIORIDADE_MIN}..{PRIORIDADE_MAX}: {r}")
    if r.custo < 0:
        raise ValueError(f"custo negativo: {r}")


def criticidade_registro(r: Registro) -> int:
    """Criticidade de um registro (inteiro, escala 1/ESCALA).

    Fórmula (u = consumo / capacidade):

        prioridade * [ 100 (u - U_REF) + PENALIDADE_EXCESSO * 100 * max(0, u - 1) ]
        + PESO_CUSTO * (custo / CUSTO_REF - 1)

    * Termo de utilização ``100 (u - U_REF)``: **pode ser negativo** (folga) ou
      positivo (pressão sobre a capacidade). Isso é essencial: se toda hora
      tivesse criticidade positiva, o "maior intervalo acumulado" seria
      trivialmente a série inteira. Com folgas negativas, somar horas
      tranquilas *reduz* o acumulado e o problema vira achar o trecho contínuo
      em que a pressão supera a folga (subarray de soma máxima).
    * ``prioridade`` multiplica: pressão sobre unidade essencial vale mais.
    * ``penalidade por excesso``: consumir além da capacidade (apagão/racionamento) é
      muito pior que apenas estar perto do limite.
    * ``custo``: preço acima da referência indica escassez.
    """
    validar_registro(r)
    u = r.consumo / r.capacidade
    excesso = max(0.0, u - 1.0)
    valor = (r.prioridade * (100.0 * (u - U_REF) + PENALIDADE_EXCESSO * 100.0 * excesso)
             + PESO_CUSTO * (r.custo / CUSTO_REF - 1.0))
    return round(ESCALA * valor)


def serie_horaria(registros: Iterable[Registro]) -> list[PontoHorario]:
    """Agrega os registros por timestamp (soma de todas as unidades) — O(R log H)."""
    acumulado: dict[datetime, list] = {}
    for r in registros:
        item = acumulado.setdefault(r.timestamp, [0.0, 0.0, 0])
        item[0] += r.consumo
        item[1] += r.capacidade
        item[2] += criticidade_registro(r)
    return [PontoHorario(t, round(c, 2), round(k, 2), crit)
            for t, (c, k, crit) in sorted(acumulado.items())]


class IndiceEnergia:
    """Índices sobre os registros para responder às consultas da Parte A."""

    def __init__(self, registros: Sequence[Registro]) -> None:
        if not registros:
            raise ValueError("é preciso pelo menos um registro")
        for r in registros:
            validar_registro(r)
        # list ordenada por tempo: base de tudo (fatias contíguas e bisect)
        self.registros: list[Registro] = sorted(
            registros, key=lambda r: (r.timestamp, r.regiao, r.unidade))
        self._por_regiao: dict[str, list[int]] = defaultdict(list)
        self._por_hora_do_dia: dict[int, list[int]] = defaultdict(list)
        self.regioes: set[str] = set()
        for i, r in enumerate(self.registros):
            self._por_regiao[r.regiao].append(i)
            self._por_hora_do_dia[r.timestamp.hour].append(i)
            self.regioes.add(r.regiao)

        self.serie: list[PontoHorario] = serie_horaria(self.registros)
        self.timestamps: list[datetime] = [p.timestamp for p in self.serie]
        self._indice_hora: dict[datetime, int] = {t: i for i, t in enumerate(self.timestamps)}
        # somas prefixo: _prefixo[k] = soma das criticidades das k primeiras horas
        self._prefixo: list[int] = [0, *accumulate(p.criticidade for p in self.serie)]

    # ---- consumo por região / por horário --------------------------------
    def consumo_por_regiao(self, regiao: str) -> float:
        """Consumo total da região. dict acha a lista da região em O(1); soma O(k)."""
        if regiao not in self._por_regiao:
            raise ValueError(f"região desconhecida: {regiao}")
        return sum(self.registros[i].consumo for i in self._por_regiao[regiao])

    def consumo_total_por_regiao(self) -> dict[str, float]:
        return {r: self.consumo_por_regiao(r) for r in sorted(self._por_regiao)}

    def perfil_horario(self, regiao: str | None = None) -> dict[int, float]:
        """Consumo médio por hora do dia (0..23), opcionalmente de uma região."""
        if regiao is not None and regiao not in self._por_regiao:
            raise ValueError(f"região desconhecida: {regiao}")
        perfil = {}
        for hora, indices in sorted(self._por_hora_do_dia.items()):
            valores = [self.registros[i].consumo for i in indices
                       if regiao is None or self.registros[i].regiao == regiao]
            if valores:
                perfil[hora] = sum(valores) / len(valores)
        return perfil

    # ---- picos ------------------------------------------------------------
    def top_picos(self, k: int) -> list[Pico]:
        """Os k maiores consumos horários do sistema, do maior para o menor.

        Min-heap de tamanho k: cada hora custa O(log k) (só entra se superar o
        menor dos k já guardados) => O(n log k), melhor que ordenar tudo, O(n log n).
        """
        if k <= 0:
            raise ValueError("k deve ser positivo")
        heap: list[tuple[float, int]] = []
        for i, p in enumerate(self.serie):
            if len(heap) < k:
                heapq.heappush(heap, (p.consumo, i))
            elif p.consumo > heap[0][0]:
                heapq.heapreplace(heap, (p.consumo, i))
        return [Pico(c, self.timestamps[i], i) for c, i in sorted(heap, reverse=True)]

    # ---- períodos críticos ------------------------------------------------
    def horas_criticas_por_regiao(self, limiar: float = 0.95) -> dict[str, set[int]]:
        """Para cada região, o *conjunto* de horas com utilização >= limiar."""
        consumo: dict[tuple[str, int], float] = defaultdict(float)
        capacidade: dict[tuple[str, int], float] = defaultdict(float)
        for r in self.registros:
            chave = (r.regiao, self._indice_hora[r.timestamp])
            consumo[chave] += r.consumo
            capacidade[chave] += r.capacidade
        criticas: dict[str, set[int]] = {reg: set() for reg in self.regioes}
        for (reg, hora), c in consumo.items():
            if c / capacidade[(reg, hora)] >= limiar:
                criticas[reg].add(hora)
        return criticas

    def horas_criticas_em_comum(self, regioes: Iterable[str], limiar: float = 0.95) -> set[int]:
        """Horas críticas simultâneas em todas as regiões dadas (interseção de sets)."""
        por_regiao = self.horas_criticas_por_regiao(limiar)
        conjuntos = []
        for reg in regioes:
            if reg not in por_regiao:
                raise ValueError(f"região desconhecida: {reg}")
            conjuntos.append(por_regiao[reg])
        return set.intersection(*conjuntos) if conjuntos else set()

    @staticmethod
    def agrupar_periodos(horas: set[int]) -> list[tuple[int, int]]:
        """Transforma um conjunto de horas em períodos contínuos ``(inicio, fim)``."""
        periodos: list[tuple[int, int]] = []
        for h in sorted(horas):
            if periodos and h == periodos[-1][1] + 1:
                periodos[-1] = (periodos[-1][0], h)
            else:
                periodos.append((h, h))
        return periodos

    # ---- seleção de intervalos -------------------------------------------
    def indices_do_intervalo(self, inicio: datetime, fim: datetime) -> tuple[int, int]:
        """Índices ``[i, j]`` (inclusivos) das horas com ``inicio <= t <= fim`` — O(log n)."""
        if fim < inicio:
            raise ValueError("fim anterior ao início")
        i = bisect.bisect_left(self.timestamps, inicio)
        j = bisect.bisect_right(self.timestamps, fim) - 1
        if i > j:
            raise ValueError("nenhuma medição no intervalo pedido")
        return i, j

    def soma_criticidade(self, i: int, j: int) -> int:
        """Soma das criticidades das horas ``i..j`` em O(1) (somas prefixo)."""
        if not 0 <= i <= j < len(self.serie):
            raise ValueError("intervalo inválido")
        return self._prefixo[j + 1] - self._prefixo[i]

    def serie_criticidade(self) -> list[int]:
        """Sequência de criticidade por hora (entrada dos algoritmos da Parte B/C)."""
        return [p.criticidade for p in self.serie]
