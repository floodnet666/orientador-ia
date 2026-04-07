import asyncio
import pytest
from app.agents.debate.context_analyzer import analyze_context, DebateContext
from app.state.graph_state import CanvasState

@pytest.mark.asyncio
async def test_analyze_context_success_with_typed_dict():
    """Valida que a correção funciona com TypedDict (BackendState)."""
    # Simula o BackendState (TypedDict)
    mock_state = {
        "project_id": "test-uuid-123",
        "academic_level": "PHD",
        "debate_round_number": 1,
        "current_canvas": CanvasState(
            tema={"content": "Mecânica Quântica", "is_locked": False},
            problema={"content": "Dualidade onda-partícula", "is_locked": False}
        ),
        "previous_debate_summary": "Resumo anterior"
    }
    
    # Invocação da função corrigida
    context = await analyze_context(mock_state, "Explique a dualidade")
    
    # Verificações de Integridade
    assert isinstance(context, DebateContext)
    assert context.project_id == "test-uuid-123"
    assert context.academic_level == "PHD"
    assert context.canvas["tema"]["content"] == "Mecânica Quântica"
    assert context.debate_intent in ["DEVELOP_PROBLEMA", "FREE_DEBATE", "DEVELOP_JUSTIFICATIVA", "DEVELOP_OBJETIVOS", "DEVELOP_METODOLOGIA"]
    
    print("\n✅ [GREEN] analyze_context validado com sucesso para TypedDict.")

@pytest.mark.asyncio
async def test_analyze_context_success_with_pydantic_object():
    """Valida que a correção também funciona com objetos Pydantic (GraphState)."""
    from app.state.graph_state import GraphState
    
    mock_state = GraphState(
        project_id="pydantic-uuid",
        user_id="user-123", # Campo obrigatório faltante detectado pelo TDD
        academic_level="PHD",
        current_canvas=CanvasState(
            tema={"content": "IA Generativa", "is_locked": False}
        )
    )
    
    context = await analyze_context(mock_state, "Debate sobre IA")
    
    assert context.project_id == "pydantic-uuid"
    assert context.canvas["tema"]["content"] == "IA Generativa"
    assert context.academic_level == "PHD"
    print("\n✅ [GREEN] analyze_context validado com sucesso para Pydantic Object.")

if __name__ == "__main__":
    asyncio.run(test_analyze_context_success_with_typed_dict())
    asyncio.run(test_analyze_context_success_with_pydantic_object())
