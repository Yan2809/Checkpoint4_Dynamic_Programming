"""Geração reprodutível (SEED) e leitura/escrita dos dados da Questão 2.

PROCESSO DE GERAÇÃO (tudo vem de ``random.Random(seed)``; mesma seed => mesmos dados)

Para cada região (5) existem ``unidades_por_regiao`` unidades consumidoras, medidas
de hora em hora durante ``n_horas`` horas a partir de ``inicio``.

1. Por unidade: capacidade-base (90-140 MWh), fração média de uso (0,62-0,76),
   prioridade fixa (1-5, mais comum 3) e um fator individual (0,9-1,1).
2. Por região: hora do pico diário (18-20 h) e amplitude do perfil diário.
3. Consumo(t) = capacidade-base x fração x perfil diário(hora) x fator de fim de
   semana (0,92) x onda de calor(t) x ruído N(1; 0,03).
   * perfil diário = 1 + amplitude*cos(2π(hora - pico)/24)
   * ondas de calor: eventos de 6-30 h por região que elevam o consumo em até
     20-45% (formato senoidal: sobe e desce suavemente).
4. Capacidade disponível(t) = capacidade-base x (1 + 0,06 sen(2π(hora-6)/24) [solar]
   + ruído N(0; 0,02)) x fator de indisponibilidade (eventos de 4-12 h com -10 a -25%).
5. Custo(t) [R$/MWh] = 150 + 500 x max(0, uso - 0,6) + ruído N(0; 8) (preço sobe com a escassez).
"""
from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from .config import SEED_GRUPO
from .estruturas_energia import REGIOES, Registro, validar_registro

ARQ_DADOS = "problema2.csv"
ARQ_META = "problema2_meta.json"
INICIO_PADRAO = datetime(2026, 1, 1)
_COLUNAS = ["timestamp", "regiao", "unidade", "consumo_mwh", "capacidade_mwh", "prioridade", "custo_rs_mwh"]
_FORMATO = "%Y-%m-%d %H:%M"


def _janela_de_eventos(rng: random.Random, n_horas: int, por_evento: int,
                       duracao: tuple[int, int], fator: tuple[float, float],
                       suave: bool) -> list[float]:
    """Vetor multiplicativo (1.0 = sem efeito) com eventos sorteados."""
    efeito = [1.0] * n_horas
    for _ in range(max(1, n_horas // por_evento)):
        dur = rng.randint(*duracao)
        ini = rng.randint(0, max(0, n_horas - 1))
        alvo = rng.uniform(*fator)
        for k in range(dur):
            t = ini + k
            if t >= n_horas:
                break
            forca = math.sin(math.pi * (k + 0.5) / dur) if suave else 1.0
            efeito[t] *= 1.0 + (alvo - 1.0) * forca
    return efeito


def gerar_registros(seed: int = SEED_GRUPO, n_horas: int = 720, unidades_por_regiao: int = 2,
                    inicio: datetime = INICIO_PADRAO) -> list[Registro]:
    """Gera ``5 x unidades_por_regiao x n_horas`` registros (ver docstring do módulo)."""
    if n_horas < 1:
        raise ValueError("n_horas deve ser >= 1")
    if unidades_por_regiao < 1:
        raise ValueError("unidades_por_regiao deve ser >= 1")
    rng = random.Random(seed)
    registros: list[Registro] = []
    por_unidade: list[list[Registro]] = []

    for regiao in REGIOES:
        pico = rng.randint(18, 20)
        amplitude = rng.uniform(0.12, 0.22)
        calor = _janela_de_eventos(rng, n_horas, 240, (6, 30), (1.20, 1.45), suave=True)
        falha = _janela_de_eventos(rng, n_horas, 300, (4, 12), (0.75, 0.90), suave=False)
        for u in range(1, unidades_por_regiao + 1):
            cap_base = rng.uniform(90, 140)
            uso_medio = rng.uniform(0.62, 0.76)
            prioridade = rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 2, 1])[0]
            fator_un = rng.uniform(0.9, 1.1)
            serie: list[Registro] = []
            for h in range(n_horas):
                t = inicio + timedelta(hours=h)
                perfil = 1.0 + amplitude * math.cos(2 * math.pi * (t.hour - pico) / 24)
                fim_semana = 0.92 if t.weekday() >= 5 else 1.0
                consumo = (cap_base * uso_medio * fator_un * perfil * fim_semana * calor[h]
                           * rng.gauss(1.0, 0.03))
                solar = 1.0 + 0.06 * math.sin(2 * math.pi * (t.hour - 6) / 24)
                capacidade = cap_base * (solar + rng.gauss(0.0, 0.02)) * falha[h]
                uso = consumo / capacidade
                custo = max(50.0, 150.0 + 500.0 * max(0.0, uso - 0.6) + rng.gauss(0.0, 8.0))
                serie.append(Registro(t, regiao, f"{regiao[:2].upper()}-{u:02d}",
                                      round(consumo, 2), round(capacidade, 2), prioridade,
                                      round(custo, 2)))
            por_unidade.append(serie)

    for serie in por_unidade:
        registros.extend(serie)
    registros.sort(key=lambda r: (r.timestamp, r.regiao, r.unidade))
    return registros


def salvar_registros(registros: list[Registro], pasta: str | Path, seed: int | None = None,
                     parametros: dict | None = None) -> None:
    """Grava ``problema2.csv`` e ``problema2_meta.json`` (seed e parâmetros)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / ARQ_DADOS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_COLUNAS)
        for r in registros:
            w.writerow([r.timestamp.strftime(_FORMATO), r.regiao, r.unidade, r.consumo,
                        r.capacidade, r.prioridade, r.custo])
    with open(pasta / ARQ_META, "w", encoding="utf-8") as f:
        json.dump({"seed": seed, "registros": len(registros), **(parametros or {})}, f, indent=2)


def carregar_registros(pasta: str | Path) -> list[Registro]:
    """Lê ``problema2.csv`` validando cada linha."""
    caminho = Path(pasta) / ARQ_DADOS
    if not caminho.is_file():
        raise FileNotFoundError(f"arquivo obrigatório ausente: {caminho}")
    registros = []
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        faltando = set(_COLUNAS) - set(leitor.fieldnames or [])
        if faltando:
            raise ValueError(f"colunas ausentes no CSV: {sorted(faltando)}")
        for linha in leitor:
            r = Registro(datetime.strptime(linha["timestamp"], _FORMATO), linha["regiao"],
                         linha["unidade"], float(linha["consumo_mwh"]),
                         float(linha["capacidade_mwh"]), int(linha["prioridade"]),
                         float(linha["custo_rs_mwh"]))
            validar_registro(r)
            registros.append(r)
    return registros
