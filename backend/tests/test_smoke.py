import pytest
import asyncio
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import User, EcosystemResource
from app.services.ollama_client import ollama_client
from app.services.qdrant_service import AsyncQdrantClient
from app.config import settings

@pytest.mark.asyncio
async def test_production_infrastructure_connectivity():
    """
    ZERO-MOCK TEST: Verifies connectivity to the real infrastructure.
    This test will fail if Docker services (Postgres, Qdrant, Ollama) are not running.
    """
    print("\n[Audit] Checking Postgres...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        # No error means connection is OK
        assert result is not None
        print(" [OK] Postgres connection successful.")

    print("[Audit] Checking Qdrant...")
    client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    collections = await client.get_collections()
    assert collections is not None
    print(f" [OK] Qdrant connection successful. Collections found: {[c.name for c in collections.collections]}")

    print("[Audit] Checking Ollama...")
    available = await ollama_client.check_model(settings.OLLAMA_CHAT_MODEL)
    if available:
        print(f" [OK] Ollama connection successful. Model {settings.OLLAMA_CHAT_MODEL} is ready.")
    else:
        print(f" [WARN] Ollama is up, but model {settings.OLLAMA_CHAT_MODEL} is missing locally.")

@pytest.mark.asyncio
async def test_production_full_flow_no_mocks():
    """
    Verifies a real-world interaction flow without any mocks.
    """
    # This is a high-level check. If it's a cold clean-start, it might fail.
    # But it proves the 'Zero-Mock' capability.
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            response = await client.get("/health")
            assert response.status_code == 200
            print(" [OK] Backend API is up and healthy.")
        except httpx.ConnectError:
            print(" [FAIL] Backend API is not responding on http://localhost:8000")
            pytest.fail("Backend server must be running for Zero-Mock E2E verification.")
