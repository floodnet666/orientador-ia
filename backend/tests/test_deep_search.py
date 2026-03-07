import pytest
import asyncio
from typing import Dict, Any

from app.lib.tools.external_search import DeepSearchTool

# Zero mocks policy:
# We will execute a real integration test against ArXiv, OpenAlex, and SciELO.
# If any of the external APIs are down/timeout, the tool gracefully returns 
# empty results for that specific source according to its `try/except` logic.

@pytest.mark.asyncio
async def test_deep_search_tool_integration():
    """
    Testa integração REAl das APIs abertas (ArXiv, OpenAlex, SciELO).
    """
    tool = DeepSearchTool()
    
    # We use a broad term likely to appear in all indices to ensure non-empty results
    query = "quantum computing"
    
    result = await tool.func(query)
    
    # Assert return structure
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "success"
    
    # Check that it returns papers (or gracefully handles if everything is down, 
    # though unlikely for all 3 huge public APIs).
    if "total_papers_found" in result:
        assert isinstance(result["total_papers_found"], int)
        assert isinstance(result["papers"], list)
        
        sources_found = set(p["source"] for p in result["papers"])
        
        # We expect at least ArXiv and OpenAlex to work almost always.
        # SciELO might not have english papers for 'quantum computing' as reliably, 
        # but it shouldn't crash.
        print(f"Sources successfully queried: {sources_found}")
        
        for paper in result["papers"]:
            assert "title" in paper
            assert "authors" in paper
            assert "url" in paper
            assert "source" in paper
            # Check length constraint to avoid LLM bloat
            assert len(result["papers"]) <= (DeepSearchTool.MAX_RESULTS_PER_SOURCE * 3)
            
    else:
        # Failsafe path
        assert result["message"] == "A pesquisa não encontrou resultados em nenhuma das fontes."
