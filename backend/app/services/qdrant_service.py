from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    SparseVectorParams,
    SparseIndexParams,
    SparseVector,
)
from rank_bm25 import BM25Okapi
import re
import math
import hashlib
from collections import Counter
from unidecode import unidecode
from uuid import UUID

from app.config import settings


_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )
    return _client


ALMAS_COLLECTION = "almas_catalog"


async def ensure_almas_collection() -> None:
    client = get_qdrant()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if ALMAS_COLLECTION not in names:
        await client.create_collection(
            collection_name=ALMAS_COLLECTION,
            vectors_config={
                "dense": VectorParams(
                    size=settings.OLLAMA_EMBED_DIMENSIONS, 
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            },
        )

# ─────────────────────────────────────────────────────────────────────────────
# GARGALO D — SPLADE-style Sparse Vectors (Consistência Global)
# ─────────────────────────────────────────────────────────────────────────────

_SPARSE_VOCAB_SIZE = 30_000  # Espaço de índices partilhado

def compute_sparse_vector_splade(text: str) -> dict:
    """
    Calcula vector esparso por token hashing com normalização linguística.
    
    Aplica lower(), unidecode (acentos) e filtro de comprimento.
    Garante que 'Educação' e 'educacao' gerem o mesmo índice.
    """
    # Normalização: lowercase e remove acentos
    text_norm = unidecode(text.lower())
    
    # Tokenização (mínimo 3 caracteres para evitar ruído)
    tokens = re.findall(r'\b[a-z]{3,}\b', text_norm)
    if not tokens:
        return {"indices": [], "values": []}

    tf = Counter(tokens)
    total_unique = len(tf)
    norm = math.sqrt(total_unique) if total_unique > 0 else 1.0

    # Hashing determinístico
    index_values: dict[int, float] = {}
    for token, count in tf.items():
        # abs(hash()) em Python é sensível à sessão (PYTHONHASHSEED). 
        # Usamos MD5 para garantir consistência entre restarts do container.
        h = hashlib.md5(token.encode()).hexdigest()
        idx = int(h, 16) % _SPARSE_VOCAB_SIZE
        
        weight = math.log1p(count) / norm
        index_values[idx] = index_values.get(idx, 0.0) + weight

    if not index_values:
        return {"indices": [], "values": []}

    # Normalização Final (Max = 1.0)
    max_val = max(index_values.values())
    indices = sorted(index_values.keys())
    values = [float(index_values[i] / max_val) for i in indices]

    return {"indices": indices, "values": values}


# ─────────────────────────────────────────────────────────────────────────────
# GARGALO C — PERSISTÊNCIA DE COLECÇÃO & MULTI-DOCUMENTO
# ─────────────────────────────────────────────────────────────────────────────

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
    PointStruct,
    SparseVector,
)

async def ensure_empirical_collection_v2() -> str:
    """Garante que a colecção v2 existe com suporte híbrido."""
    collection_name = "empirical_data_v2"
    client = get_qdrant()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    
    if collection_name not in names:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=768, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            },
        )
    return collection_name

async def delete_project_document(project_id: str, filename: str) -> None:
    """Apaga apenas os chunks de um documento específico num projecto."""
    client = get_qdrant()
    await client.delete(
        collection_name="empirical_data_v2",
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="project_id", match=models.MatchValue(value=project_id)),
                    models.FieldCondition(key="filename", match=models.MatchValue(value=filename)),
                ]
            )
        ),
    )

async def upsert_empirical_chunk(
    collection_name: str,
    chunk, 
    dense_vector: list[float],
    sparse_data: dict,
    project_id: str,
    filename: str
) -> None:
    """Insere um chunk com metadados de fonte e vectores híbridos."""
    client = get_qdrant()
    
    # ID baseada no chunk_id para evitar duplicação
    h = hashlib.md5(chunk.chunk_id.encode()).hexdigest()
    point_id = str(UUID(hex=h))

    await client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=point_id,
                vector={
                    "dense": dense_vector,
                    "sparse": SparseVector(
                        indices=sparse_data["indices"],
                        values=sparse_data["values"]
                    ),
                },
                payload={
                    "project_id": project_id,
                    "filename": filename,
                    "source_title": filename, # Gargalo A - Source Identity
                    "text": chunk.text_enriched,
                    "text_raw": chunk.text_raw,
                    "section_title": chunk.section_title,
                    "page_number": chunk.page_number,
                    "bbox": chunk.bbox,
                    "type": "empirical_evidence_v2"
                }
            )
        ]
    )
