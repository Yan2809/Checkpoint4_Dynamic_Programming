"""Estruturas de dados centrais da Questão 1 (logística de emergência).

Por que estas estruturas (justificativa pelas operações executadas):

* ``dict[int, dict[int, float]]`` (lista de adjacência) -> o grafo é esparso
  (E << V^2). Percorrer os vizinhos de ``u`` custa O(grau(u)) e consultar o
  peso de uma via custa O(1). Uma matriz V x V gastaria O(V^2) de memória e
  obrigaria a varrer V colunas para achar os vizinhos de um vértice.
* ``set[tuple[int, int]]`` de vias bloqueadas -> a pergunta "esta via está
  bloqueada?" é O(1) em média e o conjunto não admite duplicatas.
* ``tuple`` para a demanda do ponto e para a chave da aresta -> são imutáveis
  e *hashable*, logo podem ser chaves de dict/set e não sofrem alteração
  acidental depois de criados.
* ``dataclass(frozen=True)`` para ``Ponto`` e ``Solucao`` -> dados que não
  mudam depois de criados; a validação fica em um único lugar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

CENTRO = 0
RECURSOS = ("agua", "medicamentos", "alimentos", "higiene", "cobertores")
# Peso (kg) de uma unidade de cada recurso: converte a demanda em "carga",
# que é o que consome a capacidade do veículo (item do problema da mochila).
PESO_UNITARIO_KG = {
    "agua": 5,  # galão de 5 L
    "medicamentos": 1,  # caixa
    "alimentos": 4,  # cesta básica
    "higiene": 2,  # kit
    "cobertores": 2,  # fardo
}
PRIORIDADE_MIN, PRIORIDADE_MAX = 1, 5


def chave_aresta(u: int, v: int) -> tuple[int, int]:
    """Chave canônica (não direcionada) de uma via: ``(menor, maior)``."""
    return (u, v) if u < v else (v, u)


class Aresta(NamedTuple):
    """Via entre dois pontos. ``disponivel=False`` significa via bloqueada."""

    origem: int
    destino: int
    distancia: float
    disponivel: bool


@dataclass(frozen=True)
class Ponto:
    """Ponto de atendimento (ou o centro de distribuição, ``id == CENTRO``)."""

    id: int
    nome: str
    x: float
    y: float
    pessoas: int
    prioridade: int
    demanda: tuple[int, ...]  # unidades de cada recurso, na ordem de RECURSOS
    beneficio: int

    def __post_init__(self) -> None:
        if len(self.demanda) != len(RECURSOS):
            raise ValueError(f"demanda deve ter {len(RECURSOS)} valores (um por recurso)")
        if any(q < 0 for q in self.demanda):
            raise ValueError("quantidades de recursos não podem ser negativas")
        if self.pessoas < 0 or self.beneficio < 0:
            raise ValueError("pessoas e benefício não podem ser negativos")
        if not self.eh_centro:
            if not PRIORIDADE_MIN <= self.prioridade <= PRIORIDADE_MAX:
                raise ValueError(f"prioridade deve estar entre {PRIORIDADE_MIN} e {PRIORIDADE_MAX}")
            if self.carga_kg <= 0:
                raise ValueError("ponto de atendimento precisa de demanda positiva")

    @property
    def eh_centro(self) -> bool:
        return self.id == CENTRO

    @property
    def carga_kg(self) -> int:
        """Peso total (kg) da demanda mínima do ponto."""
        return sum(q * PESO_UNITARIO_KG[r] for r, q in zip(RECURSOS, self.demanda))


class GrafoLogistico:
    """Grafo ponderado não direcionado com vias que podem estar bloqueadas.

    Todas as vias (inclusive bloqueadas) ficam registradas em ``_arestas``;
    somente as disponíveis entram na lista de adjacência usada pelos
    algoritmos de caminho mínimo.
    """

    def __init__(self) -> None:
        self._pontos: dict[int, Ponto] = {}
        self._adj: dict[int, dict[int, float]] = {}
        self._arestas: dict[tuple[int, int], Aresta] = {}
        self._bloqueadas: set[tuple[int, int]] = set()

    # ---- construção -----------------------------------------------------
    def adicionar_ponto(self, ponto: Ponto) -> None:
        if ponto.id in self._pontos:
            raise ValueError(f"ponto {ponto.id} já existe")
        self._pontos[ponto.id] = ponto
        self._adj[ponto.id] = {}

    def adicionar_aresta(self, origem: int, destino: int, distancia: float,
                         disponivel: bool = True) -> None:
        if origem == destino:
            raise ValueError("laços (origem == destino) não são permitidos")
        for v in (origem, destino):
            if v not in self._pontos:
                raise ValueError(f"vértice {v} não existe")
        if not distancia > 0:  # também rejeita NaN
            raise ValueError("distância deve ser positiva")
        chave = chave_aresta(origem, destino)
        if chave in self._arestas:
            raise ValueError(f"via {chave} já existe")
        self._arestas[chave] = Aresta(chave[0], chave[1], float(distancia), bool(disponivel))
        if disponivel:
            self._ligar(chave, float(distancia))
        else:
            self._bloqueadas.add(chave)

    def bloquear_aresta(self, u: int, v: int) -> None:
        """Declara a via ``u-v`` indisponível (ex.: alagamento)."""
        chave = self._chave_existente(u, v)
        if chave in self._bloqueadas:
            return
        a = self._arestas[chave]
        self._arestas[chave] = a._replace(disponivel=False)
        self._bloqueadas.add(chave)
        del self._adj[chave[0]][chave[1]]
        del self._adj[chave[1]][chave[0]]

    def liberar_aresta(self, u: int, v: int) -> None:
        """Reabre uma via antes bloqueada."""
        chave = self._chave_existente(u, v)
        if chave not in self._bloqueadas:
            return
        a = self._arestas[chave]
        self._arestas[chave] = a._replace(disponivel=True)
        self._bloqueadas.discard(chave)
        self._ligar(chave, a.distancia)

    def _ligar(self, chave: tuple[int, int], distancia: float) -> None:
        self._adj[chave[0]][chave[1]] = distancia
        self._adj[chave[1]][chave[0]] = distancia

    def _chave_existente(self, u: int, v: int) -> tuple[int, int]:
        chave = chave_aresta(u, v)
        if chave not in self._arestas:
            raise ValueError(f"via {chave} não existe")
        return chave

    # ---- consulta -------------------------------------------------------
    def tem_ponto(self, v: int) -> bool:
        return v in self._pontos

    def ponto(self, v: int) -> Ponto:
        try:
            return self._pontos[v]
        except KeyError:
            raise ValueError(f"vértice {v} não existe") from None

    def vertices(self) -> list[int]:
        return sorted(self._pontos)

    def pontos_atendimento(self) -> list[Ponto]:
        """Todos os pontos exceto o centro de distribuição, ordenados por id."""
        return [self._pontos[v] for v in sorted(self._pontos) if v != CENTRO]

    def vizinhos(self, u: int) -> dict[int, float]:
        """Vizinhos alcançáveis por vias *disponíveis* (não modifique o retorno)."""
        if u not in self._adj:
            raise ValueError(f"vértice {u} não existe")
        return self._adj[u]

    def arestas(self) -> list[Aresta]:
        return [self._arestas[k] for k in sorted(self._arestas)]

    def esta_bloqueada(self, u: int, v: int) -> bool:
        return chave_aresta(u, v) in self._bloqueadas

    @property
    def num_vertices(self) -> int:
        return len(self._pontos)

    @property
    def num_arestas(self) -> int:
        return len(self._arestas)

    @property
    def num_arestas_disponiveis(self) -> int:
        return len(self._arestas) - len(self._bloqueadas)

    @property
    def num_arestas_bloqueadas(self) -> int:
        return len(self._bloqueadas)

    def eh_completo(self) -> bool:
        n = self.num_vertices
        return self.num_arestas == n * (n - 1) // 2


@dataclass(frozen=True)
class Instancia:
    """Um problema completo: grafo + capacidade do veículo + seed usada."""

    grafo: GrafoLogistico
    capacidade: int
    seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.capacidade, int) or self.capacidade < 0:
            raise ValueError("capacidade deve ser um inteiro >= 0 (kg)")
        if not self.grafo.tem_ponto(CENTRO):
            raise ValueError("o grafo precisa conter o centro de distribuição (id 0)")


@dataclass(frozen=True)
class Solucao:
    """Resultado de uma estratégia (gulosa ou DP)."""

    nome: str
    ordem: tuple[int, ...]  # sequência de atendimento (ids)
    beneficio: int
    carga: int
    distancia: float  # rota CD -> ... -> CD pelos caminhos mínimos
    nao_atendidos: tuple[int, ...]

    @property
    def atendidos(self) -> frozenset[int]:
        return frozenset(self.ordem)
