import pytest
from app.services import qdrant_service
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ensure_almas_collection(mocker):
    mock_client = AsyncMock()
    mock_client.get_collections.return_value = mocker.Mock(collections=[])
    
    mocker.patch("app.services.qdrant_service.get_qdrant", return_value=mock_client)
    
    await qdrant_service.ensure_almas_collection()
    mock_client.create_collection.assert_called_once()

@pytest.mark.asyncio
async def test_upsert_alma(mocker):
    mock_client = AsyncMock()
    mocker.patch("app.services.qdrant_service.get_qdrant", return_value=mock_client)
    
    await qdrant_service.upsert_alma("id1", [0.1], {"meta": "data"})
    mock_client.upsert.assert_called_once()

@pytest.mark.asyncio
async def test_search_almas(mocker):
    mock_client = AsyncMock()
    mock_result = mocker.Mock(id="id1", score=0.9, payload={"meta": "data"})
    mock_client.search.return_value = [mock_result]
    
    mocker.patch("app.services.qdrant_service.get_qdrant", return_value=mock_client)
    
    results = await qdrant_service.search_almas([0.1], "THEORETICAL")
    assert len(results) == 1
    assert results[0]["id"] == "id1"
    assert results[0]["score"] == 0.9
    assert results[0]["meta"] == "data"
