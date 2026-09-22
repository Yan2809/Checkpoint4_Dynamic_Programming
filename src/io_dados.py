"""Leitura e escrita do conjunto de dados da Questão 1 (CSV + JSON de metadados)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .estruturas import RECURSOS, GrafoLogistico, Instancia, Ponto

ARQ_PONTOS = "problema1.csv"
ARQ_ARESTAS = "problema1_arestas.csv"
ARQ_META = "problema1_meta.json"
_COLUNAS_PONTOS = ["id", "nome", "x", "y", "pessoas", "prioridade", *RECURSOS, "carga_kg", "beneficio"]


def salvar_instancia(instancia: Instancia, pasta: str | Path) -> None:
    """Grava ``problema1.csv`` (pontos), ``problema1_arestas.csv`` e ``problema1_meta.json``."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    g = instancia.grafo
    with open(pasta / ARQ_PONTOS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_COLUNAS_PONTOS)
        for v in g.vertices():
            p = g.ponto(v)
            w.writerow([p.id, p.nome, p.x, p.y, p.pessoas, p.prioridade, *p.demanda,
                        p.carga_kg, p.beneficio])
    with open(pasta / ARQ_ARESTAS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["origem", "destino", "distancia_km", "disponivel"])
        for a in g.arestas():
            w.writerow([a.origem, a.destino, a.distancia, int(a.disponivel)])
    with open(pasta / ARQ_META, "w", encoding="utf-8") as f:
        json.dump({"seed": instancia.seed, "capacidade_kg": instancia.capacidade}, f, indent=2)


def carregar_instancia(pasta: str | Path) -> Instancia:
    """Reconstrói a instância a partir dos arquivos gravados por ``salvar_instancia``."""
    pasta = Path(pasta)
    for nome in (ARQ_PONTOS, ARQ_ARESTAS, ARQ_META):
        if not (pasta / nome).is_file():
            raise FileNotFoundError(f"arquivo obrigatório ausente: {pasta / nome}")
    grafo = GrafoLogistico()
    with open(pasta / ARQ_PONTOS, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            grafo.adicionar_ponto(Ponto(
                id=int(linha["id"]), nome=linha["nome"], x=float(linha["x"]), y=float(linha["y"]),
                pessoas=int(linha["pessoas"]), prioridade=int(linha["prioridade"]),
                demanda=tuple(int(linha[r]) for r in RECURSOS), beneficio=int(linha["beneficio"]),
            ))
    with open(pasta / ARQ_ARESTAS, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            grafo.adicionar_aresta(int(linha["origem"]), int(linha["destino"]),
                                   float(linha["distancia_km"]), linha["disponivel"] == "1")
    with open(pasta / ARQ_META, encoding="utf-8") as f:
        meta = json.load(f)
    return Instancia(grafo, int(meta["capacidade_kg"]), meta.get("seed"))
