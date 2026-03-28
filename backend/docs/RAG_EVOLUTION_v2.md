# RAG Evolution v2.1.0 - Ingestão Contextual e Busca Híbrida

Este documento descreve as mudanças introduzidas na versão 2.1.0 do sistema RAG do Orientador IA, focada em fidelidade estrutural de documentos académicos e precisão na recuperação.

## Arquitectura do Pipeline (M1-M3)

### M1: Extracção para Markdown Estruturado
Utilizamos `pymupdf4llm` para converter PDFs em Markdown.
- **Vantagem:** Preserva títulos (`#`), tabelas e fórmulas LaTeX.
- **Impacto:** Melhora drasticamente a compreensão de tabelas que antes eram lidas como texto corrido desordenado.

### M2: Contextual Retrieval (Enriquecimento)
Cada chunk de texto é prefixado com metadados contextuais gerados via LLM (`qwen3.5:0.8b`).
- **Formato do Chunk:**
  ```text
  [DOC: Resumo global do documento]
  [SEC: Título da Secção actual]
  [CONTEXTO: Frase situacional do parágrafo]
  
  {Texto Original}
  ```
- **Sincronização:** As chamadas ao Ollama são serializadas com um semáforo de tamanho 1 para respeitar a política `OLLAMA_NUM_PARALLEL=1`.

### M3: Busca Híbrida (Hybrid Search)
A indexação no Qdrant agora utiliza dois motores em paralelo:
1. **Dense Vector (Denso):** `nomic-embed-text-v2-moe:latest` (768d) para busca semântica.
2. **Sparse Vector (Esparso):** BM25 (`rank_bm25`) para busca por palavras-chave exactas e termos técnicos.

---

## Novos Componentes

- `app/services/pdf_markdown_extractor.py`: Lógica de extracção e chunking estruturado.
- `app/services/contextual_enricher.py`: Orquestração do enriquecimento via Ollama.
- `app/services/hybrid_search.py`: Lógica de query combinada (Dense + Sparse).
- `app/services/qdrant_service.py`: Actualizado para suportar vectores esparsos e nova colecção `empirical_data_v2`.

## Como Verificar

### Testes Unitários
```bash
uv run pytest tests/test_pdf_markdown_extractor.py
uv run pytest tests/test_contextual_enricher.py
```

### Script de Verificação E2E
```bash
$env:PYTHONPATH="."; uv run python verify_rag_v2.py
```

---
**Nota:** A colecção anterior `empirical_data` foi mantida para compatibilidade, mas os novos uploads usam o pipeline v2.1.0.
