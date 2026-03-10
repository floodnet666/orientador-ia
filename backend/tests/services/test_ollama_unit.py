import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ollama_client import OllamaClient
from app.config import settings

@pytest.mark.asyncio
async def test_ollama_check_model_success():
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "qwen3.5:4b"}]}
    
    with patch.object(client.client, 'get', new_callable=AsyncMock, return_value=mock_resp):
        result = await client.check_model("qwen3.5:4b")
        assert result is True

@pytest.mark.asyncio
async def test_ollama_check_model_failure():
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "llama3"}]}
    
    with patch.object(client.client, 'get', new_callable=AsyncMock, return_value=mock_resp):
        result = await client.check_model("qwen3.5:4b")
        assert result is False

@pytest.mark.asyncio
async def test_ollama_embed_success():
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    
    with patch.object(client.client, 'post', new_callable=AsyncMock, return_value=mock_resp):
        emb = await client.embed("test text")
        assert emb == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_ollama_chat_complete_success():
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "Hello world"}}
    
    with patch.object(client.client, 'post', new_callable=AsyncMock, return_value=mock_resp):
        resp = await client.chat_complete("model", [{"role": "user", "content": "hi"}])
        assert resp == "Hello world"
