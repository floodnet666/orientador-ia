import pytest
from unittest.mock import AsyncMock, patch
from app.agents.debate.context_analyzer import DebateContext
from app.lib.graph.subgraphs.debate_subgraph import _execute_turn, DebateState, DebateTurn

@pytest.mark.asyncio
async def test_semantic_rigor_anti_ia_and_groupthink():
    """Valida se as instruções de turno (RolePrompts) injetam o rigor Anti-IA e Anti-Groupthink."""
    
    # Mock do estado do debate
    state = DebateState(
        original_user_message="Como a física quântica explica a consciência?",
        canvas_summary="Projeto: Consciência Quântica. Sujeito: Observador.",
        rag_context=None,
        turns=[],
        current_turn_index=0,
        panel=None,
        synthesis=None,
        synthesis_structured=None,
        is_complete=False
    )

    # Mock do LLM para capturar o Prompt enviado
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="Resposta simulada de Adam Smith.")
    
    with patch("app.lib.graph.subgraphs.debate_subgraph.get_llm", return_value=mock_llm):
        # 1. Testar Alma Primária (Anti-IA)
        await _execute_turn(state, "primaria")
        
        # O prompt enviado ao LLM deve conter as PROIBIÇÕES
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_prompt = call_args[0].content
        
        assert "PROIBIÇÃO: Nunca use frases servis" in system_prompt
        assert "Fale como o autor original" in system_prompt
        print("\n✅ Rigor Anti-IA injetado na Primária.")

        # 2. Testar Alma Complementar (Anti-Groupthink)
        mock_llm.reset_mock()
        state["turns"] = [DebateTurn(alma_id="1", alma_name="Einstein", alma_role="primaria", content="...")]
        await _execute_turn(state, "complementar")
        
        system_prompt_comp = mock_llm.ainvoke.call_args[0][0][0].content
        assert "ANTI-GROUPTHINK: Evite concordar passivamente" in system_prompt_comp
        assert "PROIBIÇÃO: Nunca use frases de assistente de IA" in system_prompt_comp
        print("✅ Rigor Anti-Groupthink injetado na Complementar.")

        # 3. Testar Alma Metodológica (Rigor Técnico)
        mock_llm.reset_mock()
        await _execute_turn(state, "metodologica")
        system_prompt_meth = mock_llm.ainvoke.call_args[0][0][0].content
        assert "AUDITORIA TÉCNICA" in system_prompt_meth
        assert "incoerência entre teoria e método" in system_prompt_meth
        print("✅ Rigor Metodológico injetado na Metodológica.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_semantic_rigor_anti_ia_and_groupthink())
