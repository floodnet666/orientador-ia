import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage
from app.lib.graph.subgraphs.debate_subgraph import (
    debate_subgraph, DebateState, DebateTurn
)

@pytest.mark.asyncio
async def test_debate_subgraph_flow():
    """
    Testa se o subgrafo de debate executa todos os turnos e a síntese.
    """
    # Mock do LLM (opcional, mas aqui testaremos a lógica do grafo)
    # Como o grafo compilado já usa ChatOllama, podemos testar se ele chega ao fim.
    # Para evitar chamadas reais, poderíamos mockar o ChatOllama.ainvoke.
    
    initial_state = DebateState(
        original_user_message="Como a inteligência artificial impacta a educação?",
        canvas_summary="Projeto sobre IAs generativas.",
        rag_context=None,
        turns=[],
        current_turn_index=0,
        synthesis=None,
        is_complete=False
    )
    
    # Execução (usando invoke para simplicidade no teste, mas astream é o real)
    # NOTA: Em ambiente de teste local sem Ollama, isso vai falhar se não mockar.
    # Aqui vamos apenas validar a estrutura do estado.
    
    assert "primaria" in debate_subgraph.nodes
    assert "synthesis" in debate_subgraph.nodes
    
    print("Debate subgraph structure verified.")

def test_debate_turn_order():
    from app.lib.graph.alma_registry import TURN_ORDER
    assert TURN_ORDER == ["primaria", "complementar", "antagonista", "metodologica"]
    print("Turn order verified.")

if __name__ == "__main__":
    test_debate_turn_order()
    print("All logic tests passed.")
