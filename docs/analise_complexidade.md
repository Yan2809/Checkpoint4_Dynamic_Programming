# Análise de complexidade

## Questão 1 — Logística de emergência

### Parâmetros

| Símbolo | Significado | Valor na instância principal |
|---|---|---|
| `V` | vértices (CD + pontos) | 21 |
| `E` | arestas **disponíveis** (as bloqueadas não entram no grafo de busca) | 40 |
| `N` | regiões candidatas (alcançáveis a partir do CD), `N < V` | 20 |
| `K` | regiões efetivamente atendidas, `K ≤ N` | 7 |
| `C` | capacidade do veículo (kg, inteiro) | 498 |

### 1. Dijkstra (`src/grafos.py::dijkstra`)

* **Estrutura:** min-heap (`heapq`) com pares `(distância provisória, vértice)` e *lazy deletion*.
* **Tempo:** cada via `{u,v}` é examinada quando `u` é fechado e quando `v` é fechado, portanto há no máximo `2E` relaxações e, no pior caso, `2E` inserções no heap.
  Cada inserção/remoção custa `O(log |heap|)` e `|heap| ≤ 2E ≤ V²`, logo `log |heap| = O(log V)`.
  Como cada vértice é fechado uma vez (entradas obsoletas são descartadas em `O(1)` cada após sair do heap), o total é `O(E log V)`.
* **Espaço:** dicionários de distância e predecessor `O(V)` + heap `O(E)` ⇒ `O(V + E)`.
* Por que não uma lista simples para achar o mínimo: seriam `V` extrações × `O(V)` cada = `O(V²)`; para grafo esparso (`E ≈ 2V`) o heap é assintoticamente melhor.

### 2. BFS de alcançabilidade (`pontos_alcancaveis`)

Cada vértice entra uma vez na `deque` e cada aresta é olhada duas vezes ⇒ `O(V + E)` tempo, `O(V)` espaço.

### 3. Guloso (`src/greedy.py`)

* **Distâncias:** o score precisa de `d(posição atual, j)`. O guloso consulta o Dijkstra da origem CD e de cada ponto visitado ⇒ no máximo `K + 1` execuções de Dijkstra
  (o cache `TabelaDistancias` impede repetições) ⇒ `O(K · E log V)` tempo e `O(K · V)` espaço.
* **Decisões:** o laço externo executa no máximo `K + 1 ≤ N + 1` vezes (cada volta atende um ponto ou encerra). Em cada volta:
  filtrar pendentes que ainda cabem `O(|pendentes|)` + calcular o score de cada um (`O(1)`: divisão e consulta ao dicionário de distâncias) + `max` sobre eles `O(|pendentes|)`.
  Como `|pendentes| ≤ N`, temos `Σ_{k=0}^{K} (N − k) ≤ (K+1)·N = O(N²)` no pior caso.
* **Total:** `O(K · E log V + N²)` tempo; espaço `O(N)` (conjunto de pendentes e lista de pontuações) `+ O(K · V)` do cache.
* **Por que não usar heap para os scores:** o score depende da posição atual, portanto **todas** as chaves mudam a cada passo. Reconstruir o heap custa `O(N)`,
  o mesmo que a varredura. O heap só valeria a pena com score estático (aí seria `O(N log N)` no total).

### 4. Programação dinâmica (`src/dynamic_programming.py`)

* **Estado:** `DP[i][c]`, com `i ∈ [0, N]` e `c ∈ [0, C]` ⇒ `(N+1)·(C+1)` estados.
* **Custo por estado:** uma comparação e uma soma (`max(DP[i-1][c], DP[i-1][c-w_i] + b_i)`) ⇒ `O(1)`.
* **Tempo:** `Θ(N · C)`. Os dois laços aninhados (`i` de 1 a N; `c` de 0 a C) são exatamente esse produto — não há recursão nem outro fator escondido.
* **Espaço:**
  * tabela completa `list[list[int]]`: `Θ(N · C)` — necessária para **reconstruir** a solução e para desenhar a Figura 3;
  * só o valor ótimo (`melhor_valor_1d`): `Θ(C)`, pois a linha `i` só depende da linha `i-1` (percorrendo `c` de trás para frente para não reutilizar o mesmo item).
    A reconstrução da escolha exigiria a tabela completa (ou a técnica de Hirschberg, não implementada).
* **Reconstrução:** um passo por linha, de `N` até 1 ⇒ `O(N)`.
* **Pseudopolinomial:** `C` aparece como *valor*. A entrada ocupa `O(log C)` bits para representar `C`, logo o tempo é exponencial no tamanho da entrada em bits.
  Na prática (kg inteiros, `C ≈ 500`) isso é irrelevante; com `C` em gramas (`≈ 500 000`) a tabela teria 1000× mais células.
* **Truque de reaproveitamento:** a última linha `DP[N][c]` já traz o ótimo de **todas** as capacidades `c ≤ C`, por isso a varredura da Parte D usa uma única tabela `Θ(N · C_max)`.

### 5. Ordenação da rota (vizinho mais próximo)

`K` iterações × `O(K)` candidatos × `O(1)` consulta de distância ⇒ `O(K²)`. É uma heurística: a ordem ótima é o problema do caixeiro-viajante (NP-difícil).

### 6. Resumo

| Etapa | Tempo | Espaço |
|---|---|---|
| Dijkstra (1 origem) | `O(E log V)` | `O(V + E)` |
| Alcançabilidade (BFS) | `O(V + E)` | `O(V)` |
| Guloso (decisões) | `O(N²)` | `O(N)` |
| Guloso (com distâncias) | `O(K·E log V + N²)` | `O(N + K·V)` |
| DP (tabela completa) | `Θ(N·C)` | `Θ(N·C)` |
| DP (só o valor) | `Θ(N·C)` | `Θ(C)` |
| Reconstrução | `O(N)` | `O(K)` |
| Ordenação vizinho mais próximo | `O(K²)` | `O(K)` |
| **Pipeline (guloso + DP)** | `O(K·E log V + N·C)` | `O(N·C + K·V)` |

### 7. Relação com os experimentos (ver `notebooks/questao1.ipynb`)

* Contagem exata de células da DP: `21 × 499 = 10 479` na instância principal (milissegundos).
* Dobrando `N` (com `C` fixo) o tempo da DP dobra aproximadamente; dobrando `C` (com `N` fixo) o tempo cresce igual ou um pouco acima do linear
  (efeitos de memória/cache com tabelas grandes). A tendência confirma `Θ(N·C)`; o desvio mostra que a notação O ignora custos de hardware.

---

## Questão 2 — Gestão inteligente do consumo de energia

### Parâmetros

| Símbolo | Significado | Valor na instância principal |
|---|---|---|
| `R` | registros (unidade × hora) | 7 200 |
| `n` | horas da série agregada (entrada dos algoritmos de intervalo) | 720 |
| `h` | níveis da recursão do D&C | ⌈log₂ n⌉ + 1 = 11 |

### 0. Pré-processamento (Parte A)

| Operação | Tempo | Espaço |
|---|---|---|
| Ordenar registros por (tempo, região, unidade) | `O(R log R)` | `O(R)` |
| Índices `dict` por região e por hora do dia | `O(R)` | `O(R)` |
| Série horária + criticidade por hora | `O(R)` | `O(n)` |
| Somas prefixo | `O(n)` | `O(n)` |
| `consumo_por_regiao` | `O(k)`, k = registros da região | `O(1)` |
| `top_picos(k)` (min-heap de tamanho k) | `O(n log k)` | `O(k)` |
| `horas_criticas_por_regiao` (sets) | `O(R)` | `O(n)` |
| `indices_do_intervalo` (bisect) | `O(log n)` | `O(1)` |
| `soma_criticidade` (prefixos) | `O(1)` | `O(1)` |

### 1. Força bruta cúbica (`brute_force.forca_bruta_cubica`)

* **Laços:** `i` (início) × `j ≥ i` (fim) × `k ∈ [i, j]` (soma do trecho, recalculada do zero).
* **Tempo:** `T(n) = Σ_{i=0}^{n-1} Σ_{j=i}^{n-1} (j − i + 1) = n(n+1)(n+2)/6 = Θ(n³)`.
  Conferido em código: n = 720 ⇒ 62 467 440 somas (= 720·721·722/6).
* **Espaço:** `S(n) = O(1)` — só escalares; não há recursão nem estruturas auxiliares.

### 2. Força bruta quadrática (`forca_bruta_quadratica`)

* **Laços:** `i` × `j ≥ i`; a soma de `[i, j]` é a de `[i, j−1]` mais `a[j]` (soma corrente), então o terceiro laço desaparece.
* **Tempo:** `T(n) = Σ_{i=0}^{n-1} (n − i) = n(n+1)/2 = Θ(n²)`. Conferido: n = 720 ⇒ 259 560 somas.
* **Espaço:** `S(n) = O(1)`.

### 3. Dividir e conquistar (`divide_conquer.dividir_e_conquistar`)

* **Chamadas recursivas:** duas por nó interno (esquerda e direita); a árvore de recursão é binária com `n` folhas e `n − 1` nós internos
  (confirmado: 719 nós registrados para n = 720).
* **Trabalho fora das chamadas:** o caso que atravessa a divisão percorre `[lo, mid]` e `[mid+1, hi]` uma vez cada ⇒ `hi − lo + 1` somas ⇒ `Θ(tamanho do subproblema)`;
  DIVIDE e COMBINE são `O(1)`.
* **Recorrência:** `T(n) = 2 T(n/2) + Θ(n)`, `T(1) = Θ(1)`.
* **Resolução por árvore de recursão:** no nível `ℓ` há `2^ℓ` subproblemas de tamanho `n/2^ℓ`, logo o trabalho por nível é `2^ℓ · Θ(n/2^ℓ) = Θ(n)`;
  com `⌈log₂ n⌉ + 1` níveis, `T(n) = Θ(n log n)`. (Teorema Mestre, caso 2: `a = b = 2`, `f(n) = Θ(n^{log_b a}) = Θ(n)`.)
  Operações contadas ≈ `n·(⌈log₂ n⌉ + 1)`: n = 720 ⇒ 7 616 (limite 720·11 = 7 920); n = 10⁶ ⇒ 20 951 424.
* **Profundidade da recursão:** `⌈log₂ n⌉ + 1` (11 para n = 720; 21 para n = 10⁶) — muito abaixo do limite de recursão do Python (1000) mesmo para milhões de horas.
* **Espaço:** cada quadro guarda `lo`, `hi`, `mid`, três tuplas de 3 inteiros ⇒ `O(1)`; profundidade `O(log n)` ⇒ `S(n) = O(log n)` auxiliar.
  A recursão usa **índices, não fatias** (`serie[lo:hi]` copiaria e daria `O(n log n)` de memória).
  O `trace` opcional (usado só para a Figura 2) guarda `n − 1` nós ⇒ `O(n)`; não faz parte do algoritmo avaliado.
* **Armazenamento intermediário:** nenhum vetor auxiliar — o melhor sufixo/prefixo é mantido em duas variáveis.

### 4. Resumo

| Algoritmo | Tempo `T(n)` | Espaço `S(n)` | n = 5 000 (medido) | n = 10⁶ |
|---|---|---|---|---|
| Força bruta cúbica | `Θ(n³)` | `O(1)` | não executada (≈ 13 min extrapolado) | ≈ 200 anos (extrapolado) |
| Força bruta quadrática | `Θ(n²)` | `O(1)` | ≈ 1,7 s | ≈ 19 h (extrapolado; 5·10¹¹ somas) |
| Dividir e conquistar | `Θ(n log n)` | `O(log n)` | ≈ 11 ms | ≈ 2,7 s (medido; 2·10⁷ operações) |

### 5. Relação com os experimentos (Parte D)

* Regressão log-log do tempo: expoentes ≈ 2,9–3,0 (cúbica), ≈ 2,0 (quadrática) e ≈ 1,0–1,1 (D&C; `n log n` aparece como reta de inclinação um pouco acima de 1 em escala log-log).
* Dobrar `n` multiplica o tempo da quadrática por ≈ 4 (até 4,7 por efeitos de cache) e o do D&C por ≈ 2.
* As contagens de operações coincidem com as fórmulas exatas (`n(n+1)/2`, `n(n+1)(n+2)/6`) e com `n(⌈log₂ n⌉+1)` para o D&C.
* Em `n` pequeno (≈ 100) a vantagem de tempo do D&C é menor que a de operações (a recursão custa mais por operação); a vantagem assintótica aparece com `n` de algumas centenas em diante.

### 6. Se o conjunto crescer de 1.000 para 1.000.000 de registros, qual solução continua viável?

Somente o **dividir e conquistar**. Multiplicar `n` por 1000 multiplica a força bruta por 10⁶ (quadrática) ou 10⁹ (cúbica); o D&C cresce
`(10⁶ · 20)/(10³ · 10) ≈ 2000×` em operações (≈ 1300× em tempo medido), ficando em poucos segundos, com pilha de 21 níveis.
O que ocupa memória é a própria série (1 milhão de inteiros), não o algoritmo.
Nota: existe uma varredura linear `O(n)` (soma corrente / Kadane) para este mesmo problema, usada apenas como referência de correção nos testes; entre as duas abordagens exigidas, o D&C é a única escalável.
