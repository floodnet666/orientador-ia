
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.qdrant_service import ensure_almas_collection, search_almas, ALMAS_COLLECTION

@pytest.mark.asyncio
async def test_ensure_almas_collection_exists():
    mock_client = AsyncMock()
    # Mock collections representation
    mock_collection_info = MagicMock()
    mock_collection_info.name = ALMAS_COLLECTION
    
    mock_collections_res = MagicMock()
    mock_collections_res.collections = [mock_collection_info]
    mock_client.get_collections.return_value = mock_collections_res
    
    with patch('app.services.qdrant_service.get_qdrant', return_value=mock_client):
        await ensure_almas_collection()
        # Should not call create_collection if it exists
        mock_client.create_collection.assert_not_called()

@pytest.mark.asyncio
async def test_ensure_almas_collection_creates():
    mock_client = AsyncMock()
    mock_collections_res = MagicMock()
    mock_collections_res.collections = []
    mock_client.get_collections.return_value = mock_collections_res
    
    with patch('app.services.qdrant_service.get_qdrant', return_value=mock_client):
        await ensure_almas_collection()
        mock_client.create_collection.assert_called_once()

@pytest.mark.asyncio
async def test_search_almas_success():
    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_point = MagicMock(id=1, score=0.9, payload={"name": "test"})
    mock_result.points = [mock_point]
    mock_client.query_points.return_value = mock_result
    
    with patch('app.services.qdrant_service.get_qdrant', return_value=mock_client):
        results = await search_almas([0.1]*768, "theoretical")
        assert len(results) == 1
        assert results[0]["name"] == "test"
        assert results[0]["score"] == 0.9
