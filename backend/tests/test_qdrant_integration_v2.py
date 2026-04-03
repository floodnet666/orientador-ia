import pytest
import uuid
from app.services.qdrant_service import index_alma, search_almas, get_qdrant
from app.services.ollama_client import ollama_client
from app.models.sql_models import EcosystemResource
from app.config import settings

@pytest.mark.asyncio
async def test_alma_indexing_and_search_uqa_flow():
    """
    ZERO-MOCK INTEGRATION TEST:
    1. Creates a temporary Alma model.
    2. Indexes it into Qdrant using the real Ollama embedding.
    3. Searches for it using the new query_points (UQA) logic.
    4. Verifies the result matches and has correct score/payload.
    """
    # 1. Setup unique test Alma
    test_id = uuid.uuid4()
    test_name = f"Test Alma {test_id}"
    test_desc = "Especialista em testes de integração e auditoria de infraestrutura Qdrant."
    
    mock_alma = EcosystemResource(
        id=test_id,
        name=test_name,
        description=test_desc,
        alma_type="METHODOLOGICAL",
        is_approved=True
    )

    print(f"\n[Integration] Indexing test Alma: {test_name}")
    try:
        # 2. Index (Uses Ollama + Qdrant Upsert)
        await index_alma(mock_alma)
        
        # 3. Wait for consistency (Qdrant is near-real-time)
        import asyncio
        await asyncio.sleep(1)

        # 4. Search (Uses Ollama + Qdrant query_points)
        print(f"[Integration] Searching for keywords: 'auditoria infraestrutura'")
        query_vector = await ollama_client.embed("auditoria infraestrutura")
        
        results = await search_almas(query_vector, alma_type="METHODOLOGICAL", top_k=5)
        
        # 5. Assertions
        assert len(results) > 0, "No results found for test Alma search"
        
        # Find our specific alma in results
        found = any(r["name"] == test_name for r in results)
        assert found, f"Test Alma '{test_name}' not found in search results: {[r['name'] for r in results]}"
        
        # Verify payload mapping (v9.1.5 refactor check)
        best_hit = next(r for r in results if r["name"] == test_name)
        assert "score" in best_hit
        assert best_hit["alma_type"] == "METHODOLOGICAL"
        assert "personality_descriptor" in best_hit
        
        print(f" [OK] Integration flow successful. Match found with score {best_hit['score']}")

    finally:
        # 6. Cleanup
        print(f"[Integration] Cleaning up test point from Qdrant...")
        client = get_qdrant()
        from app.services.qdrant_service import ALMAS_COLLECTION
        from qdrant_client import models
        
        # Point ID is CRC32 of UUID-string in current implementation
        from zlib import crc32
        point_id = crc32(str(test_id).encode())
        
        await client.delete(
            collection_name=ALMAS_COLLECTION,
            points_selector=models.PointIdsList(points=[point_id]),
            wait=True
        )
        print(" [OK] Cleanup complete.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_alma_indexing_and_search_uqa_flow())
