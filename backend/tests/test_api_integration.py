import sys
import os
import unittest.mock as mock
import pytest
import json

# Setup paths
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Disable database and external calls before importing app
# We patch the base engine and sessionmaker
with mock.patch("sqlalchemy.create_engine"), \
     mock.patch("sqlalchemy.ext.asyncio.create_async_engine"), \
     mock.patch("app.database.engine"), \
     mock.patch("app.database.AsyncSessionLocal"), \
     mock.patch("qdrant_client.AsyncQdrantClient"), \
     mock.patch("arxiv.Search"), \
     mock.patch("fitz.open"), \
     mock.patch("pandas.read_csv"):
    
    # Import app and TestClient inside the mocked context
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.auth import create_token

client = TestClient(app)

def get_auth_headers():
    token = create_token("test@user.com")
    return {"Authorization": f"Bearer {token}"}

def test_api_ping():
    # Simple check to ensure the app is loaded
    response = client.get("/")
    assert response.status_code in [200, 404] # Root might be 404 but app should respond

def test_empirical_upload_api():
    projectId = "12345678-1234-1234-1234-123456789012"
    fake_file = ("test.pdf", b"pdf content", "application/pdf")
    
    with mock.patch("app.services.empirical.document_processor.EmpiricalProcessor.process_pdf", return_value="text"), \
         mock.patch("app.services.qdrant_service.qdrant_service.upsert_points"):
        
        response = client.post(
            f"/api/empirical/{projectId}/upload",
            files={"file": fake_file},
            headers=get_auth_headers()
        )
        assert response.status_code == 200
        assert response.json()["filename"] == "test.pdf"

def test_genesis_api():
    payload = {"prompt": "test prompt"}
    
    # Mock the LLM stream
    async def mock_chat_stream(*args, **kwargs):
        yield {"content": '```json\n{"name": "Test Alma", "description": "desc", "type": "THEORETICAL", "system_prompt": "..."}\n```'}

    with mock.patch("app.services.ollama_client.ollama_client.chat_stream", side_effect=mock_chat_stream), \
         mock.patch("app.services.qdrant_service.qdrant_service.index_alma"):
        
        response = client.post(
            "/api/almas/genesis",
            json=payload,
            headers=get_auth_headers()
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Alma"

def test_ferramenteiro_execute_api():
    payload = {"code": "print('ok')", "context": {}}
    response = client.post(
        "/api/almas/execute",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

if __name__ == "__main__":
    # Run tests directly
    test_api_ping()
    test_empirical_upload_api()
    test_genesis_api()
    test_ferramenteiro_execute_api()
    print("ALL API INTEGRATION TESTS PASSED!")
