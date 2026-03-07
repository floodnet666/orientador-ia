import pytest
from app.services.ollama_client import OllamaClient
from unittest.mock import AsyncMock, patch

@pytest.fixture
def ollama():
    return OllamaClient()

@pytest.mark.asyncio
async def test_ollama_chat_complete(ollama, mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "Hello from AI"}}
    mock_resp.raise_for_status = mocker.Mock()
    
    mocker.patch.object(ollama.client, 'post', return_value=mock_resp)
    
    result = await ollama.chat_complete("model", [{"role": "user", "content": "hi"}])
    assert result == "Hello from AI"
    ollama.client.post.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_embed(ollama, mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_resp.raise_for_status = mocker.Mock()
    
    mocker.patch.object(ollama.client, 'post', return_value=mock_resp)
    
    result = await ollama.embed("text")
    assert result == [0.1, 0.2, 0.3]
    ollama.client.post.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_check_model_available(ollama, mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "llama3:latest"}]}
    mock_resp.raise_for_status = mocker.Mock()
    
    mocker.patch.object(ollama.client, 'get', return_value=mock_resp)
    
    result = await ollama.check_model("llama3")
    assert result is True

@pytest.mark.asyncio
async def test_ollama_check_model_unavailable(ollama, mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "mistral"}]}
    
    mocker.patch.object(ollama.client, 'get', return_value=mock_resp)
    
    result = await ollama.check_model("llama3")
    assert result is False
