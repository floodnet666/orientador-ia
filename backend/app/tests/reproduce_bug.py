import pytest
from pydantic import ValidationError
from app.agents.debate.context_analyzer import DebateContext
from app.state.graph_state import CanvasState

def test_debate_context_validation_failure():
    """Simula a falha reportada no log original."""
    # O log mostrou passatem de CanvasState onde se espera dict, e campos faltando.
    invalid_canvas = CanvasState()
    
    with pytest.raises(ValidationError) as excinfo:
        # Tentativa de instanciação manual incompleta (como estava no graph_factory.py)
        DebateContext(
            canvas=invalid_canvas,
            user_message="Quero debater meu problema."
        )
    
    errors = excinfo.value.errors()
    field_names = [e['loc'][0] for e in errors]
    
    assert "project_id" in field_names
    assert "debate_intent" in field_names
    assert "academic_level" in field_names
    # O erro de tipo no 'canvas' também deve estar lá
    assert any(e['loc'][0] == "canvas" and e['type'] == "dict_type" for e in errors)
    print("\n✅ [RED] Falha de contrato reproduzida com sucesso.")

if __name__ == "__main__":
    pytest.main([__file__])
