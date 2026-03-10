import sys
import os
import unittest.mock as mock
import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

# Setup paths
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import app
from app.main import app
from app.api.auth import create_token, get_current_user
from app.database import get_db
from app.models.sql_models import User

@pytest.fixture
async def async_client():
    # Setup overrides for this test module
    async def override_get_current_user():
        import uuid
        return User(
            id=uuid.UUID("12345678-1234-1234-1234-123456789012"), 
            is_admin=True, 
            email="admin@test.com"
        )

    async def override_get_db():
        from unittest.mock import AsyncMock
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

def get_auth_headers():
    token = create_token("12345678-1234-1234-1234-123456789012")
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_api_ping(async_client):
    response = await async_client.get("/")
    assert response.status_code in [200, 404]

@pytest.mark.asyncio
async def test_empirical_upload_api(async_client):
    projectId = "12345678-1234-1234-1234-123456789012"
    fake_file = ("test.pdf", b"pdf content", "application/pdf")
    
    with mock.patch("app.services.empirical.document_processor.EmpiricalProcessor.process_pdf", return_value="text"), \
         mock.patch("app.services.empirical.document_processor.EmpiricalProcessor.index_document", new_callable=mock.AsyncMock):
        
        response = await async_client.post(
            f"/api/empirical/{projectId}/upload",
            files={"file": fake_file},
            headers=get_auth_headers()
        )
        assert response.status_code == 200
        assert "processed" in response.json()["message"]

@pytest.mark.asyncio
async def test_genesis_api(async_client):
    payload = {"prompt": "test prompt"}
    
    # Mock the LLM stream
    async def mock_chat_stream(*args, **kwargs):
        yield {"content": '```json\n{"name": "Test Alma", "description": "desc", "type": "THEORETICAL", "system_prompt": "..."}\n```'}

    with mock.patch("app.services.genesis_service.ollama_client.chat_stream", side_effect=mock_chat_stream), \
         mock.patch("app.api.almas.index_alma", new_callable=mock.AsyncMock):
        
        response = await async_client.post(
            "/api/almas/genesis",
            json={"description": "test prompt"},
            headers=get_auth_headers()
        )
        assert response.status_code == 200
        assert response.json()["alma"]["name"] == "Test Alma"

@pytest.mark.asyncio
async def test_ferramenteiro_execute_api(async_client):
    payload = {"code": "print('ok')", "context": {}}
    response = await async_client.post(
        "/api/almas/execute",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
