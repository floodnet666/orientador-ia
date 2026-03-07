from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

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
            vectors_config=VectorParams(
                size=settings.OLLAMA_EMBED_DIMENSIONS, distance=Distance.COSINE
            ),
        )


async def upsert_alma(
    point_id: str,
    vector: list[float],
    payload: dict,
) -> None:
    client = get_qdrant()
    await client.upsert(
        collection_name=ALMAS_COLLECTION,
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )


async def search_almas(
    vector: list[float], alma_type: str, top_k: int = 3
) -> list[dict]:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = get_qdrant()
    # DEBUG START
    print(f"DEBUG: client type={type(client)}")
    print(f"DEBUG: client attributes={[attr for attr in dir(client) if not attr.startswith('_')]}")
    # DEBUG END
    results = await client.query_points(
        collection_name=ALMAS_COLLECTION,
        query=vector,
        query_filter=Filter(
            must=[FieldCondition(key="alma_type", match=MatchValue(value=alma_type))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "id": str(r.id),
            "score": r.score,
            **r.payload,
        }
        for r in results.points
    ]


async def index_alma(alma) -> None:
    """Indexes a single Alma (EcosystemResource) into Qdrant."""
    from app.services.ollama_client import ollama_client
    from qdrant_client.models import PointStruct

    embedding = await ollama_client.embed(f"{alma.name} {alma.description}")
    client = get_qdrant()
    await client.upsert(
        collection_name=ALMAS_COLLECTION,
        points=[
            PointStruct(
                id=str(alma.id),
                vector=embedding,
                payload={
                    "name": alma.name,
                    "description": alma.description,
                    "alma_type": alma.type.value if hasattr(alma.type, 'value') else str(alma.type),
                },
            )
        ],
    )
