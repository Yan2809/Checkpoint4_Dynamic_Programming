"""Testes da Questão 2 (rodar com: pytest -q)."""
import heapq
import math
import random
from datetime import datetime, timedelta

import pytest

from src.brute_force import forca_bruta_cubica, forca_bruta_quadratica
from src.divide_conquer import dividir_e_conquistar
from src.escalabilidade import (estimar_expoente, executar_experimento, extrapolar, gerar_serie,
                                serie_sintetica)
from src.estruturas_energia import (ESCALA, IndiceEnergia, Registro, criticidade_registro,
                                    serie_horaria, validar_registro)
from src.gerador_q2 import carregar_registros, gerar_registros, salvar_registros
from src.intervalos import ResultadoIntervalo


# ---------------------------------------------------------------- helpers
def registro(hora=0, regiao="Sul", unidade="SU-01", consumo=80.0, capacidade=100.0,
             prioridade=3, custo=300.0):
    return Registro(datetime(2026, 1, 1) + timedelta(hours=hora), regiao, unidade, consumo,
                    capacidade, prioridade, custo)


def kadane_soma(serie):
    """Referência linear (só valor) para conferir os algoritmos da Parte B/C."""
    melhor = atual = serie[0]
    for x in serie[1:]:
        atual = max(x, atual + x)
        melhor = max(melhor, atual)
    return melhor


def soma_bruta_referencia(serie):
    return max(sum(serie[i:j + 1]) for i in range(len(serie)) for j in range(i, len(serie)))


# ---------------------------------------------------------- dados / gerador
class TestGerador:
    def test_requisitos_do_enunciado(self):
        regs = gerar_registros(seed=4)
        assert len(regs) >= 1000
        campos = set(Registro._fields)
        assert {"timestamp", "regiao", "consumo", "capacidade", "prioridade", "custo"} <= campos
        assert len({r.regiao for r in regs}) == 5

    def test_reprodutivel_e_seeds_diferentes(self):
        assert gerar_registros(3, n_horas=48) == gerar_registros(3, n_horas=48)
        assert gerar_registros(3, n_horas=48) != gerar_registros(4, n_horas=48)

    def test_valores_validos(self):
        for r in gerar_registros(2, n_horas=100):
            validar_registro(r)

    def test_parametros_invalidos(self):
        with pytest.raises(ValueError):
            gerar_registros(1, n_horas=0)
        with pytest.raises(ValueError):
            gerar_registros(1, unidades_por_regiao=0)

    def test_csv_ida_e_volta(self, tmp_path):
        regs = gerar_registros(5, n_horas=30)
        salvar_registros(regs, tmp_path, seed=5)
        assert carregar_registros(tmp_path) == regs

    def test_csv_ausente_ou_invalido(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            carregar_registros(tmp_path)
        (tmp_path / "problema2.csv").write_text("timestamp,regiao\n2026-01-01 00:00,Sul\n")
        with pytest.raises(ValueError):
            carregar_registros(tmp_path)


# ------------------------------------------------------------- criticidade
class TestCriticidade:
    def test_pode_ser_negativa_e_positiva(self):
        assert criticidade_registro(registro(consumo=50)) < 0  # folga
        assert criticidade_registro(registro(consumo=95)) > 0  # pressão

    def test_excesso_e_penalizado_alem_do_linear(self):
        no_limite = criticidade_registro(registro(consumo=100))
        acima = criticidade_registro(registro(consumo=110))
        passo_normal = criticidade_registro(registro(consumo=100)) - criticidade_registro(registro(consumo=90))
        passo_excesso = acima - no_limite
        assert passo_excesso > passo_normal  # depois de 100% a criticidade sobe mais rápido

    def test_prioridade_amplifica(self):
        baixa = criticidade_registro(registro(consumo=95, prioridade=1))
        alta = criticidade_registro(registro(consumo=95, prioridade=5))
        assert alta > baixa

    def test_registro_invalido(self):
        with pytest.raises(ValueError):
            criticidade_registro(registro(consumo=-1))
        with pytest.raises(ValueError):
            criticidade_registro(registro(capacidade=0))
        with pytest.raises(ValueError):
            criticidade_registro(registro(prioridade=9))
        with pytest.raises(ValueError):
            criticidade_registro(registro(custo=-5))

    def test_serie_horaria_soma_unidades(self):
        regs = [registro(0, unidade="A"), registro(0, unidade="B"), registro(1, unidade="A")]
        s = serie_horaria(regs)
        assert len(s) == 2
        assert s[0].consumo == 160.0 and s[0].criticidade == 2 * criticidade_registro(regs[0])


# --------------------------------------------------------- estruturas (A)
class TestIndice:
    @pytest.fixture(scope="module")
    def ix(self):
        return IndiceEnergia(gerar_registros(seed=7, n_horas=240))

    def test_consumo_por_regiao_confere_com_varredura(self, ix):
        for regiao in ix.regioes:
            esperado = sum(r.consumo for r in ix.registros if r.regiao == regiao)
            assert ix.consumo_por_regiao(regiao) == pytest.approx(esperado)
        assert sum(ix.consumo_total_por_regiao().values()) == pytest.approx(sum(r.consumo for r in ix.registros))

    def test_regiao_desconhecida(self, ix):
        with pytest.raises(ValueError):
            ix.consumo_por_regiao("Atlantida")
        with pytest.raises(ValueError):
            ix.perfil_horario("Atlantida")

    def test_perfil_horario(self, ix):
        perfil = ix.perfil_horario()
        assert sorted(perfil) == list(range(24))
        vals = [r.consumo for r in ix.registros if r.timestamp.hour == 19]
        assert perfil[19] == pytest.approx(sum(vals) / len(vals))

    def test_top_picos_igual_a_ordenacao(self, ix):
        esperado = sorted((p.consumo for p in ix.serie), reverse=True)[:5]
        assert [p.consumo for p in ix.top_picos(5)] == esperado
        assert len(ix.top_picos(10_000)) == len(ix.serie)  # k maior que n
        with pytest.raises(ValueError):
            ix.top_picos(0)

    def test_horas_criticas_e_periodos(self, ix):
        por_regiao = ix.horas_criticas_por_regiao(0.85)
        assert set(por_regiao) == ix.regioes
        comum = ix.horas_criticas_em_comum(["Sudeste", "Sul"], 0.85)
        assert comum == por_regiao["Sudeste"] & por_regiao["Sul"]
        assert ix.horas_criticas_em_comum([], 0.85) == set()
        with pytest.raises(ValueError):
            ix.horas_criticas_em_comum(["Atlantida"])

    def test_agrupar_periodos(self):
        assert IndiceEnergia.agrupar_periodos({1, 2, 3, 7, 9, 10}) == [(1, 3), (7, 7), (9, 10)]
        assert IndiceEnergia.agrupar_periodos(set()) == []

    def test_selecao_de_intervalo_e_soma_prefixos(self, ix):
        i, j = ix.indices_do_intervalo(datetime(2026, 1, 3), datetime(2026, 1, 4, 5))
        assert ix.timestamps[i] == datetime(2026, 1, 3, 0) and ix.timestamps[j] == datetime(2026, 1, 4, 5)
        assert ix.soma_criticidade(i, j) == sum(ix.serie_criticidade()[i:j + 1])
        with pytest.raises(ValueError):
            ix.indices_do_intervalo(datetime(2026, 1, 5), datetime(2026, 1, 4))
        with pytest.raises(ValueError):
            ix.indices_do_intervalo(datetime(2030, 1, 1), datetime(2030, 1, 2))
        with pytest.raises(ValueError):
            ix.soma_criticidade(5, 2)

    def test_indice_vazio(self):
        with pytest.raises(ValueError):
            IndiceEnergia([])


# ---------------------------------------------- força bruta e dividir/conquistar
ALGORITMOS = [forca_bruta_cubica, forca_bruta_quadratica, dividir_e_conquistar]


class TestIntervaloCritico:
    def test_exemplo_conhecido(self):
        serie = [-2, 1, -3, 4, -1, 2, 1, -5, 4]  # clássico: [3, 6] soma 6
        for alg in ALGORITMOS:
            r = alg(serie)
            assert (r.inicio, r.fim, r.soma) == (3, 6, 6)

    def test_caso_que_atravessa_o_meio(self):
        serie = [-1, 5, 5, -1]  # mid = 1: melhor intervalo [1, 2] cruza a divisão
        trace = []
        r = dividir_e_conquistar(serie, trace)
        assert (r.inicio, r.fim, r.soma) == (1, 2, 10)
        raiz = next(n for n in trace if n.nivel == 0)
        assert raiz.melhor == raiz.cruzado == (10, 1, 2)
        assert raiz.esquerda[0] == 5 and raiz.direita[0] == 5

    def test_casos_extremos(self):
        for alg in ALGORITMOS:
            assert (alg([7]).inicio, alg([7]).soma) == (0, 7)  # um elemento (caso-base)
            r = alg([-5, -2, -9])  # tudo negativo: o intervalo é o maior elemento (não vazio)
            assert (r.inicio, r.fim, r.soma) == (1, 1, -2)
            r = alg([1, 2, 3, 4])  # tudo positivo: a série inteira
            assert (r.inicio, r.fim, r.soma) == (0, 3, 10)
            r = alg([0, 0, 0])  # empate total: o mais curto e mais cedo
            assert (r.inicio, r.fim, r.soma) == (0, 0, 0)

    def test_serie_vazia(self):
        for alg in ALGORITMOS:
            with pytest.raises(ValueError):
                alg([])

    def test_tres_algoritmos_e_referencias_concordam_em_series_aleatorias(self):
        rng = random.Random(2026)
        for _ in range(400):
            n = rng.randint(1, 45)
            serie = [rng.randint(-15, 15) for _ in range(n)]
            resultados = [alg(serie) for alg in ALGORITMOS]
            assert len({(r.inicio, r.fim, r.soma) for r in resultados}) == 1  # mesmo intervalo (desempate)
            soma = resultados[0].soma
            assert soma == kadane_soma(serie) == soma_bruta_referencia(serie)
            assert sum(serie[resultados[0].inicio:resultados[0].fim + 1]) == soma

    def test_serie_real_gerada(self):
        serie = gerar_serie(300, seed=1)
        cubica, quad, dc = (alg(serie) for alg in ALGORITMOS)
        assert (cubica.inicio, cubica.fim) == (quad.inicio, quad.fim) == (dc.inicio, dc.fim)

    def test_contagem_de_operacoes_bate_com_a_teoria(self):
        n = 60
        serie = [random.Random(1).randint(-9, 9) for _ in range(n)]
        assert forca_bruta_quadratica(serie).operacoes == n * (n + 1) // 2
        assert forca_bruta_cubica(serie).operacoes == n * (n + 1) * (n + 2) // 6
        dc = dividir_e_conquistar(serie)
        assert dc.operacoes <= n * (math.ceil(math.log2(n)) + 1)

    def test_estrutura_da_recursao(self):
        n = 100
        serie = [random.Random(3).randint(-9, 9) for _ in range(n)]
        trace = []
        r = dividir_e_conquistar(serie, trace)
        assert len(trace) == n - 1  # árvore binária com n folhas tem n-1 nós internos
        assert r.profundidade == math.ceil(math.log2(n)) + 1
        raiz = [no for no in trace if no.nivel == 0]
        assert len(raiz) == 1 and (raiz[0].lo, raiz[0].hi) == (0, n - 1)
        for no in trace:  # o resultado combinado é o melhor dos três candidatos
            assert no.melhor[0] == max(no.esquerda[0], no.direita[0], no.cruzado[0])

    def test_nao_altera_a_entrada(self):
        serie = [3, -1, 4, -1, 5]
        copia = list(serie)
        for alg in ALGORITMOS:
            alg(serie)
        assert serie == copia

    def test_recursao_profunda_nao_estoura(self):
        serie = serie_sintetica(200_000, seed=1)
        assert dividir_e_conquistar(serie).profundidade == math.ceil(math.log2(200_000)) + 1

    def test_resultado_tamanho(self):
        assert ResultadoIntervalo(2, 5, 1, 1).tamanho == 4


# ---------------------------------------------------------- escalabilidade
class TestEscalabilidade:
    def test_expoente_de_potencias_exatas(self):
        ns = [10, 100, 1000]
        assert estimar_expoente(ns, [n ** 2 for n in ns]) == pytest.approx(2.0)
        assert estimar_expoente(ns, [5 * n for n in ns]) == pytest.approx(1.0)

    def test_expoente_entradas_invalidas(self):
        with pytest.raises(ValueError):
            estimar_expoente([1], [1])
        with pytest.raises(ValueError):
            estimar_expoente([5, 5], [1, 2])

    def test_extrapolacao(self):
        assert extrapolar(2.0, 100, 1000, 2.0) == pytest.approx(200.0)

    def test_experimento_pequeno(self):
        linhas = executar_experimento([50, 100], seed=1, repeticoes=1)
        assert {l.n for l in linhas} == {50, 100}
        assert {l.algoritmo for l in linhas} == {"Força bruta O(n³)", "Força bruta O(n²)", "Dividir e Conquistar"}
        for n in (50, 100):
            assert len({l.soma for l in linhas if l.n == n}) == 1  # todos concordam

    def test_experimento_tamanhos_invalidos(self):
        with pytest.raises(ValueError):
            executar_experimento([])
        with pytest.raises(ValueError):
            executar_experimento([0])

    def test_serie_tem_tamanho_pedido(self):
        assert len(gerar_serie(123, seed=2)) == 123
        assert len(serie_sintetica(77, seed=2)) == 77
