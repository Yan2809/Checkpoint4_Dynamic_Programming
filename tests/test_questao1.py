"""Testes da Questão 1 (rodar com: pytest -q)."""
import itertools
import math
import random

import pytest

from src.comparacao import (analisar_contraexemplo, comparar_capacidades, contraexemplo_proprio,
                            estatisticas_por_seed)
from src.dynamic_programming import (melhor_valor_1d, preencher_tabela,
                                     programacao_dinamica_atendimento, reconstruir)
from src.estruturas import CENTRO, RECURSOS, GrafoLogistico, Instancia, Ponto
from src.gerador_q1 import gerar_instancia
from src.grafos import (TabelaDistancias, dijkstra, distancia_da_rota, pontos_alcancaveis,
                        reconstruir_caminho)
from src.greedy import guloso_atendimento, razao_beneficio_custo
from src.io_dados import carregar_instancia, salvar_instancia


# ---------------------------------------------------------------- helpers
def ponto(id_, kg=1, beneficio=1, prioridade=3):
    """Ponto cuja carga é ``kg`` (usa apenas medicamentos, 1 kg/unidade)."""
    demanda = [0] * len(RECURSOS)
    demanda[RECURSOS.index("medicamentos")] = kg
    return Ponto(id_, f"P{id_}", 0.0, 0.0, 10, prioridade, tuple(demanda), beneficio)


def grafo_linha():
    """CD(0) - 1 - 2 - 3, cada via com 10 km; via extra 0-3 de 100 km."""
    g = GrafoLogistico()
    g.adicionar_ponto(Ponto(CENTRO, "CD", 0, 0, 0, 0, (0,) * len(RECURSOS), 0))
    for i in (1, 2, 3):
        g.adicionar_ponto(ponto(i))
    g.adicionar_aresta(0, 1, 10)
    g.adicionar_aresta(1, 2, 10)
    g.adicionar_aresta(2, 3, 10)
    g.adicionar_aresta(0, 3, 100)
    return g


def forca_bruta(pesos, beneficios, capacidade):
    """Referência exponencial (só para testar a DP em instâncias pequenas)."""
    melhor = 0
    for r in range(len(pesos) + 1):
        for combo in itertools.combinations(range(len(pesos)), r):
            if sum(pesos[i] for i in combo) <= capacidade:
                melhor = max(melhor, sum(beneficios[i] for i in combo))
    return melhor


# ------------------------------------------------------- estruturas/grafo
class TestGrafo:
    def test_rejeita_entradas_invalidas(self):
        g = grafo_linha()
        with pytest.raises(ValueError):
            g.adicionar_aresta(0, 1, 5)  # duplicada
        with pytest.raises(ValueError):
            g.adicionar_aresta(1, 1, 5)  # laço
        with pytest.raises(ValueError):
            g.adicionar_aresta(1, 99, 5)  # vértice inexistente
        with pytest.raises(ValueError):
            g.adicionar_aresta(1, 3, -2)  # distância negativa
        with pytest.raises(ValueError):
            g.adicionar_ponto(ponto(1))  # id repetido

    def test_ponto_invalido(self):
        with pytest.raises(ValueError):
            Ponto(5, "x", 0, 0, 10, 9, (1,) * 5, 1)  # prioridade fora de 1..5
        with pytest.raises(ValueError):
            Ponto(5, "x", 0, 0, 10, 3, (0,) * 5, 1)  # demanda zero
        with pytest.raises(ValueError):
            Ponto(5, "x", 0, 0, 10, 3, (1, 1), 1)  # tamanho errado

    def test_via_bloqueada_sai_da_adjacencia(self):
        g = grafo_linha()
        g.adicionar_ponto(ponto(4))
        g.adicionar_aresta(3, 4, 7, disponivel=False)
        assert g.esta_bloqueada(4, 3)
        assert 4 not in g.vizinhos(3)
        assert g.num_arestas_bloqueadas == 1
        g.liberar_aresta(3, 4)
        assert g.vizinhos(3)[4] == 7

    def test_instancia_exige_capacidade_inteira_nao_negativa(self):
        with pytest.raises(ValueError):
            Instancia(grafo_linha(), -1)


# ---------------------------------------------------------------- dijkstra
class TestDijkstra:
    def test_menor_caminho_e_reconstrucao(self):
        g = grafo_linha()
        dist, ant = dijkstra(g, 0)
        assert dist[3] == 30  # 0-1-2-3 (30) vence a via direta (100)
        assert reconstruir_caminho(ant, 0, 3) == [0, 1, 2, 3]

    def test_bloqueio_forca_desvio(self):
        g = grafo_linha()
        g.bloquear_aresta(1, 2)
        dist, _ = dijkstra(g, 0)
        assert dist[3] == 100  # só resta a via direta
        assert dist[2] == 110  # 0-3-2

    def test_inalcancavel(self):
        g = grafo_linha()
        g.bloquear_aresta(0, 1)
        g.bloquear_aresta(0, 3)
        dist, ant = dijkstra(g, 0)
        assert math.isinf(dist[1])
        assert reconstruir_caminho(ant, 0, 1) == []
        assert pontos_alcancaveis(g) == []

    def test_origem_invalida(self):
        with pytest.raises(ValueError):
            dijkstra(grafo_linha(), 42)

    def test_distancia_da_rota_inclui_retorno(self):
        g = grafo_linha()
        t = TabelaDistancias(g)
        assert distancia_da_rota([1, 2], t) == 10 + 10 + 20  # ida 0-1-2 e volta 2-1-0
        assert distancia_da_rota([], t) == 0


# ---------------------------------------------------------------- gerador
class TestGerador:
    def test_requisitos_do_enunciado(self):
        g = gerar_instancia(seed=3).grafo
        assert len(g.pontos_atendimento()) >= 20
        assert g.num_arestas >= 35
        assert g.num_arestas_disponiveis >= 35
        assert g.num_arestas_bloqueadas >= 1
        assert not g.eh_completo()
        assert len(pontos_alcancaveis(g)) == len(g.pontos_atendimento())  # conexo

    def test_reprodutivel_e_seeds_diferentes_geram_dados_diferentes(self):
        def assinatura(seed):
            inst = gerar_instancia(seed)
            return (inst.capacidade, [p.beneficio for p in inst.grafo.pontos_atendimento()],
                    [(a.origem, a.destino, a.distancia, a.disponivel) for a in inst.grafo.arestas()])
        assert assinatura(5) == assinatura(5)
        assert assinatura(5) != assinatura(6)

    def test_parametros_invalidos(self):
        with pytest.raises(ValueError):
            gerar_instancia(1, n_pontos=5, n_disponiveis=3)
        with pytest.raises(ValueError):
            gerar_instancia(1, n_pontos=3, n_disponiveis=6, n_bloqueadas=0)  # seria completo
        with pytest.raises(ValueError):
            gerar_instancia(1, fracao_capacidade=0)

    def test_csv_ida_e_volta(self, tmp_path):
        original = gerar_instancia(seed=9)
        salvar_instancia(original, tmp_path)
        lido = carregar_instancia(tmp_path)
        assert lido.capacidade == original.capacidade and lido.seed == 9
        assert lido.grafo.arestas() == original.grafo.arestas()
        assert [lido.grafo.ponto(v) for v in lido.grafo.vertices()] == \
               [original.grafo.ponto(v) for v in original.grafo.vertices()]

    def test_arquivo_ausente(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            carregar_instancia(tmp_path)


# ---------------------------------------------------------------- DP
class TestProgramacaoDinamica:
    def test_exemplo_conhecido(self):
        pesos, ben = [1, 3, 4, 5], [1, 4, 5, 7]
        tabela = preencher_tabela(pesos, ben, 7)
        assert tabela[-1][7] == 9  # itens de peso 3 e 4
        assert reconstruir(tabela, pesos, 7) == [1, 2]

    def test_caso_base(self):
        tabela = preencher_tabela([2, 3], [5, 6], 4)
        assert all(v == 0 for v in tabela[0])  # nenhuma região
        assert all(linha[0] == 0 for linha in tabela)  # capacidade 0

    def test_igual_a_forca_bruta_em_instancias_aleatorias(self):
        rng = random.Random(123)
        for _ in range(150):
            n = rng.randint(0, 9)
            pesos = [rng.randint(1, 12) for _ in range(n)]
            ben = [rng.randint(0, 30) for _ in range(n)]
            cap = rng.randint(0, 40)
            tabela = preencher_tabela(pesos, ben, cap)
            esperado = forca_bruta(pesos, ben, cap)
            assert tabela[-1][cap] == esperado
            assert melhor_valor_1d(pesos, ben, cap) == esperado
            escolhidos = reconstruir(tabela, pesos, cap)
            assert sum(pesos[i] for i in escolhidos) <= cap
            assert sum(ben[i] for i in escolhidos) == esperado

    def test_item_mais_pesado_que_a_capacidade_e_ignorado(self):
        tabela = preencher_tabela([50, 2], [999, 3], 10)
        assert reconstruir(tabela, [50, 2], 10) == [1]

    def test_entradas_invalidas(self):
        with pytest.raises(ValueError):
            preencher_tabela([1, 2], [1], 5)
        with pytest.raises(ValueError):
            preencher_tabela([0], [1], 5)
        with pytest.raises(ValueError):
            preencher_tabela([1], [1], -1)
        with pytest.raises(ValueError):
            melhor_valor_1d([1], [-1], 5)

    def test_atendimento_respeita_capacidade_e_ignora_inalcancaveis(self):
        g = gerar_instancia(seed=2).grafo
        # isola o ponto 16 bloqueando todas as suas vias disponíveis
        for viz in list(g.vizinhos(16)):
            g.bloquear_aresta(16, viz)
        tabela = TabelaDistancias(g)
        sol, resultado = programacao_dinamica_atendimento(g, 300, tabela)
        assert 16 not in sol.ordem and 16 not in resultado.candidatas
        assert sol.carga <= 300


# ---------------------------------------------------------------- guloso
class TestGuloso:
    def test_score(self):
        assert razao_beneficio_custo(60, 6, 1, lam=0.5) == pytest.approx(60 / 6.5)
        with pytest.raises(ValueError):
            razao_beneficio_custo(1, 0, 0)

    def test_respeita_capacidade(self):
        for seed in range(1, 21):
            inst = gerar_instancia(seed)
            sol = guloso_atendimento(inst.grafo, inst.capacidade, TabelaDistancias(inst.grafo))
            assert sol.carga <= inst.capacidade
            assert len(set(sol.ordem)) == len(sol.ordem)

    def test_capacidade_zero_nao_atende_ninguem(self):
        g = gerar_instancia(seed=1).grafo
        sol = guloso_atendimento(g, 0, TabelaDistancias(g))
        assert sol.ordem == () and sol.beneficio == 0

    def test_nunca_visita_ponto_inalcancavel(self):
        g = grafo_linha()
        g.bloquear_aresta(0, 1)
        g.bloquear_aresta(0, 3)
        sol = guloso_atendimento(g, 100, TabelaDistancias(g))
        assert sol.ordem == ()

    def test_distancia_pesa_na_escolha(self):
        # pontos idênticos em benefício e carga: vence o mais próximo do CD (1 a 10 km, 3 a 30 km)
        g = grafo_linha()
        sol = guloso_atendimento(g, 1, TabelaDistancias(g), lam=1.0)
        assert sol.ordem == (1,)

    def test_historico_registra_passos(self):
        g = grafo_linha()
        hist = []
        guloso_atendimento(g, 2, TabelaDistancias(g), historico=hist)
        assert [h["passo"] for h in hist] == [1, 2]

    def test_parametros_invalidos(self):
        g = grafo_linha()
        with pytest.raises(ValueError):
            guloso_atendimento(g, -1, TabelaDistancias(g))
        with pytest.raises(ValueError):
            guloso_atendimento(g, 5, TabelaDistancias(g), lam=-1)


# ---------------------------------------------------- comparação/contraexemplo
class TestComparacao:
    def test_contraexemplo_guloso_nao_e_otimo(self):
        r = analisar_contraexemplo()
        assert r["guloso"].beneficio == 60
        assert r["dp"].beneficio == 90
        assert set(r["dp"].ordem) == {2, 3}
        assert r["guloso"].ordem == (1,)

    def test_contraexemplo_e_valido(self):
        inst = contraexemplo_proprio()
        assert inst.capacidade == 10
        assert [p.carga_kg for p in inst.grafo.pontos_atendimento()] == [6, 5, 5]

    def test_dp_nunca_perde_para_o_guloso(self):
        for seed in range(1, 41):
            inst = gerar_instancia(seed)
            t = TabelaDistancias(inst.grafo)
            g = guloso_atendimento(inst.grafo, inst.capacidade, t)
            d, _ = programacao_dinamica_atendimento(inst.grafo, inst.capacidade, t)
            assert d.beneficio >= g.beneficio
            assert d.carga <= inst.capacidade

    def test_varredura_extremos_guloso_e_otimo(self):
        g = gerar_instancia(seed=1).grafo
        total = sum(p.carga_kg for p in g.pontos_atendimento())
        linhas = comparar_capacidades(g, [0, total, total + 50])
        assert all(l.guloso_otimo for l in linhas)  # nada cabe / tudo cabe
        assert linhas[0].beneficio_dp == 0

    def test_varredura_vazia(self):
        assert comparar_capacidades(gerar_instancia(1).grafo, []) == []

    def test_estatisticas(self):
        s = estatisticas_por_seed(range(1, 11))
        assert s["instancias"] == 10
        assert s["guloso_otimo"] + s["guloso_subotimo"] == 10
        assert 0 <= s["perda_media_pct"] <= s["perda_maxima_pct"]
