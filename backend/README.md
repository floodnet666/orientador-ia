# Orientador.IA - Backend

## RAG v2.2.0 Stability & Audit Fixes (2026-03-25)

This update focuses on stabilizing the Docker environment and resolving critical execution crashes in the RAG pipeline.

### Architectural & Operational Fixes
- **Docker Dependency Resolution**: Added missing critical libraries for the RAG v2.2.0 pipeline:
    - `rank-bm25`: Required for the hybrid search/BM25 layer.
    - `unidecode`: Required for linguistic normalization in SPLADE-style sparse vectors.
    - `pyspellchecker`: Required for text preprocessing in the empirical processor.
- **Qdrant Client Pinning**: Hard-pinned `qdrant-client==1.12.0` to ensure absolute compatibility with the Qdrant server (v1.12.1) and resolve `TypeError` in the internal HTTP client.
- **Removed check_compatibility**: Eliminated legacy `check_compatibility=False` argument from `AsyncQdrantClient` calls (specifically in `document_processor.py`) which was causing container crashes.
- **index_alma Restored**: Resolved `ImportError` by re-implementing the `index_alma` function in `qdrant_service.py`, ensuring the Match Engine for agents remains operational.

### Environment Setup
1. Use `docker compose up --build` to apply these changes.
2. The backend service listens on port `8000`.
3. Ensure Ollama is running with the `qwen2.5:7b` model for optimal RAG performance.
