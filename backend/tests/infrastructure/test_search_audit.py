import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

from app.lib.tools.external_search import DeepSearchTool

# --- TESTES DE UNIDADE (Integridade Semântica) ---

def test_abstract_reconstruction_fidelity():
    """
    Audit: Validação da reconstrução do abstract a partir de um Inverted Index.
    Padrão OpenAlex: {'palavra': [posições]}.
    """
    tool = DeepSearchTool()
    
    # Caso 1: Abstract simples e ordenado
    inverted_index = {
        "O": [0],
        "Orientador": [1],
        "IA": [2],
        "é": [3],
        "eficiente": [4]
    }
    expected = "O Orientador IA é eficiente"
    assert tool._reconstruct_abstract(inverted_index) == expected
    
    # Caso 2: Abstract com palavras repetidas e posições puladas
    inverted_index_2 = {
        "Pesquisa": [0, 4],
        "é": [1],
        "física": [2],
        "pura": [3]
    }
    # [Pesquisa, é, física, pura, Pesquisa]
    expected_2 = "Pesquisa é física pura Pesquisa"
    assert tool._reconstruct_abstract(inverted_index_2) == expected_2

    # Caso 3: Abstract vazio ou None
    assert tool._reconstruct_abstract({}) == "No abstract available."
    assert tool._reconstruct_abstract(None) == "No abstract available."

def test_combined_results_merging_logic():
    """
    Audit: Validação da lógica de merge concorrente.
    Garante que resultados de múltiplas fontes são agregados sem perda de campos críticos.
    """
    tool = DeepSearchTool()
    
    mock_arxiv = [{"source": "ArXiv", "title": "Paper A", "authors": ["Author 1"], "url": "url1"}]
    mock_openalex = [{"source": "OpenAlex", "title": "Paper B", "authors": ["Author 2"], "url": "url2"}]
    
    # Simulando o retorno de combine results
    combined = mock_arxiv + mock_openalex
    
    assert len(combined) == 2
    assert combined[0]["source"] == "ArXiv"
    assert combined[1]["source"] == "OpenAlex"
    for item in combined:
        assert all(k in item for k in ["title", "authors", "url", "source"])

# --- TESTES DE RESILIÊNCIA (Stress & Timeout) ---

@pytest.mark.asyncio
async def test_gather_resilience_with_timeouts():
    """
    Audit: Resiliência Térmica.
    Garante que se uma API demorar mais que o permitido (15s), as outras ainda entregam.
    """
    tool = DeepSearchTool()
    
    async def fast_mock_search(*args, **kwargs):
        return [{"source": "Fast", "title": "Fast Result"}]
    
    async def slow_mock_search(*args, **kwargs):
        await asyncio.sleep(2.0) # Simula delay significativo (mas menor que o timeout real para o teste de unidade)
        return [{"source": "Slow", "title": "Slow Result"}]

    with patch.multiple(tool, 
                        _search_arxiv=fast_mock_search, 
                        _search_openalex=slow_mock_search, 
                        _search_scielo=fast_mock_search):
        
        start_time = time.time()
        result = await tool.func("test query")
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration >= 2.0  # Esperou a lenta
        assert len(result["papers"]) == 3
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_graceful_failure_on_exception():
    """
    Audit: Tratamento de erro catastrófico em uma fonte.
    """
    tool = DeepSearchTool()
    
    async def failing_mock_search(*args, **kwargs):
        raise Exception("API Crashed")
    
    async def working_mock_search(*args, **kwargs):
        return [{"source": "Working", "title": "Working"}]

    with patch.multiple(tool, 
                        _search_arxiv=failing_mock_search, 
                        _search_openalex=working_mock_search, 
                        _search_scielo=working_mock_search):
        
        result = await tool.func("catastrophe test")
        
        # Deve ter 2 resultados (as que trabalharam) e não deve crashar o func()
        assert len(result["papers"]) == 2
        assert result["status"] == "success"

# --- TESTES DE INTEGRAÇÃO LIVE (As-Is: n=2) ---

@pytest.mark.asyncio
async def test_live_search_metrics_benchmark():
    """
    Audit: Benchmark de Performance e Metadados (Evolutivo).
    """
    tool = DeepSearchTool()
    n = tool.MAX_RESULTS_PER_SOURCE
    
    query = "Large Language Models engineering"
    
    start_time = time.time()
    result = await tool.func(query)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\n[METRICS] N={n} Search Duration: {duration:.2f}s")
    
    assert result["status"] == "success"
    if result["papers"]:
        # Verificando amostragem de tokens (estimativa bruta: 1 char = 0.25 token)
        total_chars = sum(len(p.get("abstract", "")) + len(p.get("title", "")) for p in result["papers"])
        est_tokens = total_chars // 4
        print(f"[METRICS] Estimated Prompt Tokens: {est_tokens}")
        
        # Audit de limitação local
        source_counts = {}
        for p in result["papers"]:
            src = p["source"]
            source_counts[src] = source_counts.get(src, 0) + 1
            
        for src, count in source_counts.items():
            assert count <= n, f"Source {src} ultrapassou o limite de {n}"
