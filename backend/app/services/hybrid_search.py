"""
Busca híbrida: Dense (nomic-embed-text) + Sparse (BM25).
Implementa Reciprocal Rank Fusion (RRF) ou Scoring Combinado.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client import models
from app.services.qdrant_service import (
    get_qdrant, 
    compute_sparse_vector_splade
)
from app.services.ollama_client import ollama_client

async def hybrid_search_evidence(
    project_id: UUID,
    query: str,
    limit: int = 5,
    score_threshold: float = 0.15  # Gargalo B: Spread threshold para rerank
) -> List[Dict[str, Any]]:
    """
    Executa busca híbrida industrial v2.2.0.
    1. Busca Híbrida (Dense + SPLADE Sparse)
    2. Reciprocal Rank Fusion (RRF) implícito no Qdrant
    3. Reranking condicional por Spread de Score
    4. Atribuição de Fonte (Source Identity)
    """
    client = get_qdrant()
    pid_str = str(project_id)
    collection_name = "empirical_data_v2"
    
    # 1. Vetores
    dense_vector = await ollama_client.embed(query)
    sparse_data = compute_sparse_vector_splade(query)
    
    # 2. Busca Híbrida Nativa (Qdrant Prefetch)
    # Usamos prefetch para fundir os resultados
    search_results = await client.query_points(
        collection_name=collection_name,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        prefetch=[
            models.Prefetch(
                query=dense_vector,
                using="dense",
                filter=models.Filter(must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=pid_str))]),
                limit=limit * 3
            ),
            models.Prefetch(
                query=models.SparseVector(indices=sparse_data["indices"], values=sparse_data["values"]),
                using="sparse",
                filter=models.Filter(must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=pid_str))]),
                limit=limit * 3
            )
        ],
        limit=limit,
        with_payload=True,
    )

    hits = search_results.points
    if not hits:
        return []

    # 3. Reranking Condicional (Gargalo B)
    # Se a diferença entre o primeiro e o segundo resultado for grande (> threshold), 
    # pulamos o rerank pois o resultado é inequívoco.
    needs_rerank = True
    if len(hits) > 1:
        spread = hits[0].score - hits[1].score
        if spread > score_threshold:
            needs_rerank = False
            # log.info("Rerank skip: High confidence spread (%.2f)", spread)

    # Implementação simplificada do rerank (no RAG Final isto passaria por um Cross-Encoder)
    # Por agora, focamos na marcação da "Alima" com Source Identity.

    results = []
    for hit in hits:
        payload = hit.payload
        filename = payload.get("filename", "desconhecido")
        text_raw = payload.get("text_raw", payload.get("text", ""))
        
        # Atribuição de Fonte (Gargalo A Refinement)
        # Injetamos o nome da fonte diretamente no texto para que a Alma cite correctamente.
        formatted_text = f"[Fonte: {filename}] {text_raw}"
        
        results.append({
            "text": formatted_text,
            "filename": filename,
            "section": payload.get("section_title", ""),
            "page": payload.get("page_number", 0),
            "score": hit.score,
            "context": payload.get("text", ""), # texto enriquecido contextualizado
            "bbox": payload.get("bbox")
        })

    return results
