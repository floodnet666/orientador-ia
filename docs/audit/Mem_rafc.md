# Mem_rafc — Auditoria e Roadmap de Implementação RAG

> **Propósito:** Documento de rastreamento de sessão para o refactoring do pipeline RAG do Orientador IA.  
> **Criado em:** 2026-04-07  
> **Última atualização:** 2026-04-07  
> **Versão do sistema no momento desta auditoria:** RAG v2.2.0

---

## Estado Geral de Implementação

| # | Componente | Status | Ficheiros Afetados |
|---|------------|--------|--------------------|
| 1 | Filtro de Novidade (Jaccard) | ✅ **IMPLEMENTADO** | `contextual_enricher.py` |
| 2 | Busca Híbrida: Set-Union Merge (SUM) | ✅ **IMPLEMENTADO** | `hybrid_search.py` |
| 3 | Integração do NoveltyFilter na ingestão | ✅ **IMPLEMENTADO** | `document_processor.py` |
| 4 | Migração RRF → SUM na `hybrid_search_evidence` | ✅ **IMPLEMENTADO** | `hybrid_search.py` |
| 5 | Upgrade do NoveltyFilter para embedding cosine | ✅ **IMPLEMENTADO** | `contextual_enricher.py` |

---

## ✅ Componente 1: Filtro de Novidade (Jaccard)

### O que foi implementado

Classe `NoveltyFilter` adicionada ao início de `backend/app/services/contextual_enricher.py`.

```python
# Localização: backend/app/services/contextual_enricher.py (L19–L54)
class NoveltyFilter:
    def __init__(self, threshold: float = 0.85) -> None: ...
    def _tokenize(self, text: str) -> set: ...
    def _jaccard_similarity(self, set_a: set, set_b: set) -> float: ...
    def is_redundant(self, new_text: str, history: list[str]) -> bool: ...
```

**Algoritmo:** Jaccard bag-of-words com tokenização por regex (`[^\w\s]` removido, lowercased).  
**Complexidade:** O(n · |V|) onde n = |history|, |V| = vocabulário único.

### Testes (6 passing)

Localização: `backend/tests/services/test_contextual_enricher.py`

| Teste | Cobertura |
|-------|-----------|
| `test_rejects_redundant_input` | Threshold 0.65 — frases quase idênticas em PT-BR |
| `test_accepts_novel_input` | Conceito semanticamente distinto é aceite |
| `test_empty_history_never_redundant` | Edge case: histórico vazio |
| `test_exact_duplicate_is_redundant` | Cópia exacta → similaridade 1.0 |
| `test_threshold_boundary` | Threshold 1.0 — limite matemático de `>` vs `>=` |
| `test_tokenizer_strips_punctuation` | Pontuação não deve perturbar tokenização |

### ⚠️ Decisão de design crítica (LEIA ANTES DE ALTERAR O THRESHOLD)

O threshold padrão da spec original era `0.85`, calibrado para **cosine similarity de embeddings densos** (espaço contínuo de alta dimensionalidade).

**O Jaccard bag-of-words para PT-BR produz ~0.70 para frases "quase idênticas"**, não 0.85. As frases de teste verificadas:
- `"Bourdieu afirma que o habitus é uma estrutura estruturante"` vs  
  `"O habitus em Bourdieu é uma estrutura estruturante"`  
- Jaccard calculado: **0.70** (7 tokens em comum / 10 na união)

O threshold operacional nos testes é `0.65`. O padrão da classe permanece `0.85` para estar pronto para a migração futura para embeddings.

### ✅ O que estava pendente e foi resolvido: Integração no Pipeline
A classe foi importada e instanciada em `backend/app/services/empirical/document_processor.py`, no núcleo o método `process_pdf_v2`.

```python
novelty_filter = NoveltyFilter(threshold=0.65)
history_texts = []

for chunk in enriched_chunks:
    if novelty_filter.is_redundant(chunk.text_raw, history_texts):
        log.info("Chunk redundante ignorado (Jaccard): %s", chunk.chunk_id)
        continue
    # ... embed e upsert ocorrem aqui
    history_texts.append(chunk.text_raw)
```
**Resultado:** O banco de dados vetorial agora rejeita iterativamente _chunks_ que tenham 65%+ de partilha lexical (PT-BR) com _chunks_ processados anteriormente na mesma "run" de PDF, combatendo o inchaço severo. Um teste XP (`test_processor_novelty.py`) garante que a integração impede que a QDrant API seja chamada duplicadamente.

---

## ✅ Componente 2: Busca Híbrida — Set-Union Merging (SUM)

### O que foi implementado

Função pura `_set_union_merge` adicionada a `backend/app/services/hybrid_search.py` (L22–L81).

```python
def _set_union_merge(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    limit: int = 10,
    sparse_interjection_threshold: float = 20.0,
) -> List[Dict[str, Any]]:
```

**Algoritmo:** `R(q) = D(q) ⊕ (S(q) \ D(q))`

1. Insere todos os resultados densos primeiro (preserva fluidez semântica), marcando `is_anchor=False`.
2. Identifica âncoras léxicas exclusivas do esparso: `S(q) \ D(q)`.
3. Âncoras com score > `sparse_interjection_threshold` são injectadas na **posição 1**.
4. Âncoras com score ≤ threshold são **anexadas ao final**.

**Comportamento da interjecção** (importante para testes):
- `doc_3` com `score=22.1 > threshold=20.0` → posição 1 (logo após o melhor denso)
- `doc_3` com `score=5.0 ≤ threshold=20.0` → posição final

### Testes (7 passing)

Localização: `backend/tests/services/test_hybrid_search.py`

| Teste | Cobertura |
|-------|-----------|
| `test_preserves_dense_order_and_appends_sparse_anchors` | Caso canónico da spec |
| `test_no_duplication_when_sparse_subset_of_dense` | Sem duplicação |
| `test_limit_is_respected` | Respeita o parâmetro `limit` |
| `test_high_score_anchor_interjected_at_position_1` | Score alto → posição 1 |
| `test_low_score_anchor_appended_at_end` | Score baixo → final |
| `test_original_payload_not_mutated` | Imutabilidade dos inputs |
| `test_empty_dense_returns_sparse_as_anchors` | Edge case: dense vazio |

### ✅ O que estava pendente e foi resolvido: RRF → SUM no Pipeline

A função de topo `hybrid_search_evidence` (usada pelo backend REST da RAG) foi recodificada para fazer os mapeamentos independentes para `SUM`.

1. Duas **buscas independentes** e paralelas foram construídas para abolir a `Fusion.RRF` (Qdrant nativa).
2. O parser injeta também os payloads num modelo flexível.
3. Injeta a prop de origem explícita (`Source Identity`) no texto gerado pelas âncoras SUM.
4. Validada estritamente via Test-Driven Development (XP). Em `tests/services/test_hybrid_search_integration.py` garante-se que são feitas `==2` queries isoladas e que a fusão recai no nosso unificador explícito.

---

## ✅ Componente 3: Upgrade NoveltyFilter para Embeddings Cosine

### O que foi implementado

O filtro de similaridade evoluiu de Jaccard bag-of-words síncrono para métricas vetoriais semânticas via embeddings.

```python
class NoveltyFilter:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self._cache: dict[str, list[float]] = {}
        
    async def is_redundant(self, new_text: str, history: list[str]) -> bool:
        # Puxa do dict _cache em O(1), e embeda apenas textos inauditos
        ...
        similarity = self._cosine_similarity(new_emb, past_emb)
        ...
```

**Vantagem implementada:** O threshold `0.85` nativo atua agora identificando redundância semântica genuína através das relações matemáticas, e não de colisão textual pura (ignorando lexica diferente que signifique o mesmo).
**Solução de Performance:** Implementámos um Dicionário de Cache Local (LRU conceptual) na instância da classe invocada na sub-rotina do documento. Numa pipeline de 300 chunks, o histórico de embeddings não é re-pesquisado (O(n) pesado em tráfego), pois é servido do object_state interno em `O(1)`. O impacto na rede ao nó do Ollama não aumenta com o ciclo.

---

## Contexto do Sistema (para o agente da próxima sessão)

### Localização dos ficheiros principais

```
backend/
├── app/services/
│   ├── contextual_enricher.py   ← NoveltyFilter implementado aqui (L19–L54)
│   ├── hybrid_search.py         ← _set_union_merge implementado aqui (L22–L81)
│   ├── qdrant_service.py        ← Ponto de integração do NoveltyFilter
│   └── pdf_section_indexer.py   ← Alternativa de integração do NoveltyFilter
└── tests/services/
    ├── conftest.py                   ← Isola testes unitários puros do conftest raiz
    ├── test_contextual_enricher.py   ← 6 testes NoveltyFilter (todos passing)
    └── test_hybrid_search.py         ← 7 testes _set_union_merge (todos passing)
```

### Como executar os testes unitários

```powershell
# Sempre a partir de: d:\orientador.ia\orientador-ia\backend
$env:PYTHONPATH = "d:\orientador.ia\orientador-ia\backend"
uv run pytest tests/services/ -v
```

### Por que existe um `conftest.py` local em `tests/services/`

O `conftest.py` raiz de `tests/` faz `from app.main import app` e inicializa uma BD SQLite em memória. Isto é incompatível com testes unitários puros que não precisam de infraestrutura. O `conftest.py` em `tests/services/` **está vazio intencionalmente** para isolar este diretório do conftest raiz.

### Avisos de deprecação conhecidos (não-bloqueantes)

```
app/models/schemas.py — Pydantic V2: class-based Config → migrar para ConfigDict
app/main.py:115       — FastAPI: @app.on_event → migrar para lifespan handlers
```

Estes não afetam os novos componentes mas devem ser tratados numa sessão futura.

### Restrições de arquitetura

- **OLLAMA_NUM_PARALLEL=1** no docker-compose. Qualquer chamada ao Ollama dentro do NoveltyFilter semântico DEVE usar `_OLLAMA_SEMAPHORE` para serialização.
- **GENESIS_SYSTEM_PROMPT** em `genesis_service.py` está sob **bloqueio total**. Não alterar.

---

## Fronteira de Investigação Não-Resolvida

O `sparse_interjection_threshold=20.0` é um valor empírico baseado na escala de scores do BM25/SPLADE. Scores variam por corpus e modelo. **Este parâmetro precisa de calibração experimental** com dados reais do sistema antes de ser promovido como default de produção.

Abordagem sugerida: coletar distribuição de scores esparsos reais via `search_audit_out.txt` e definir percentis (ex: p95 como threshold).