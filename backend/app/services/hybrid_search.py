"""
Busca híbrida: Dense (nomic-embed-text) + Sparse (BM25/SPLADE).

Estratégias de fusão disponíveis:
- RRF (Reciprocal Rank Fusion): via Qdrant nativo — `hybrid_search_evidence`.
- SUM (Set-Union Merging): via `_set_union_merge` — R(q) = D(q) ⊕ (S(q) \\ D(q)).
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


def _set_union_merge(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    limit: int = 10,
    sparse_interjection_threshold: float = 20.0,
) -> List[Dict[str, Any]]:
    """
    Set-Union Merging (SUM) para RAG Académico.

    R(q) = D(q) ⊕ (S(q) \\ D(q))

    Garantias:
      1. Ordem densa preservada (fluidez semântica).
      2. Âncoras léxicas exclusivas do esparso são injectadas ao final
         (ou na posição 1 se score > sparse_interjection_threshold).
      3. Nenhuma duplicação (chave: doc["id"]).
      4. Resultado limitado a `limit` documentos.

    Args:
        dense_results: Lista de dicts com chaves "id", "score", "payload".
        sparse_results: Lista de dicts com chaves "id", "score", "payload".
        limit: Número máximo de resultados finais.
        sparse_interjection_threshold: Score mínimo para intercalar no topo.

    Returns:
        Lista mesclada com metadado "is_anchor" em cada payload.
    """
    merged: List[Dict[str, Any]] = []
    dense_ids: set = set()

    # 1. Inserir resultados densos — garantia de fluidez semântica
    for doc in dense_results:
        if len(merged) >= limit:
            break
        doc_copy = doc.copy()
        doc_copy["payload"] = doc_copy.get("payload", {}).copy()
        doc_copy["payload"]["is_anchor"] = False
        merged.append(doc_copy)
        dense_ids.add(doc["id"])

    # 2. Identificar âncoras léxicas: S(q) \\ D(q)
    lexical_anchors: List[Dict[str, Any]] = []
    for doc in sparse_results:
        if doc["id"] not in dense_ids:
            doc_copy = doc.copy()
            doc_copy["payload"] = doc_copy.get("payload", {}).copy()
            doc_copy["payload"]["is_anchor"] = True
            lexical_anchors.append(doc_copy)

    # 3. Interjecção ordenada (Spec §5.3)
    for anchor in lexical_anchors:
        if len(merged) >= limit:
            break
        if anchor.get("score", 0) > sparse_interjection_threshold:
            insert_pos = min(1, len(merged))
            merged.insert(insert_pos, anchor)
        else:
            merged.append(anchor)

    return merged[:limit]



async def hybrid_search_evidence(
    project_id: UUID,
    query: str,
    limit: int = 5,
    score_threshold: float = 0.15  # Gargalo B: Spread threshold para rerank
) -> List[Dict[str, Any]]:
    """
    Executa busca híbrida industrial v2.2.0.
    1. Busca Híbrida Independente (Dense + SPLADE Sparse)
    2. Set-Union Merging (SUM) R(q) = D(q) ⊕ (S(q) \ D(q))
    3. Atribuição de Fonte (Source Identity)
    """
    client = get_qdrant()
    pid_str = str(project_id)
    collection_name = "empirical_data_v2"
    
    # 1. Vetores
    dense_vector = await ollama_client.embed(query)
    sparse_data = compute_sparse_vector_splade(query)
    
    # 2. Buscas Independentes (Densa e Esparsa)
    dense_res = await client.query_points(
        collection_name=collection_name,
        query=dense_vector,
        using="dense",
        query_filter=models.Filter(must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=pid_str))]),
        limit=limit * 3,
        with_payload=True,
    )
    
    sparse_res = await client.query_points(
        collection_name=collection_name,
        query=models.SparseVector(indices=sparse_data["indices"], values=sparse_data["values"]),
        using="sparse",
        query_filter=models.Filter(must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=pid_str))]),
        limit=limit * 3,
        with_payload=True,
    )

    # 3. Conversão para dict compatível com o _set_union_merge
    dense_dicts = [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in dense_res.points]
    sparse_dicts = [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in sparse_res.points]

    # 4. Set-Union Merging (SUM)
    hits = _set_union_merge(dense_dicts, sparse_dicts, limit=limit)

    if not hits:
        return []

    results = []
    for hit in hits:
        payload = hit["payload"]
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
            "score": hit["score"],
            "context": payload.get("text", ""), # texto enriquecido contextualizado
            "bbox": payload.get("bbox"),
            "is_anchor": payload.get("is_anchor", False)
        })

    return results

