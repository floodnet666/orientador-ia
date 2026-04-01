import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.graph_factory import debate_node
from app.agents.debate.panel_selector import SelectedPanel, AlmaRole, AntagonistRole
from app.agents.state import BackendState

@pytest.mark.asyncio
async def test_debate_node_triggers_genesis_on_low_adherence():
    """
    TDD: Test Case 2 (Genesis Trigger)
    Ensure that when select_panel returns a low score, GenesisService is called.
    """
    # 1. Setup State
    state = BackendState(
        messages=[],
        project_id="test_proj",
        user_id="test_user",
        active_soul_ids=["user_alma_1"],
        canvas_nodes=[],
        is_debate_mode=True
    )

    # 2. Mock select_panel to return low adherence
    # We'll use a mocked return value with a score of 0.4
    low_score_panel = SelectedPanel(
        PRIMARIA=AlmaRole(alma_id="1", alma_name="Foucault", selection_rationale="OK", score=0.9),
        COMPLEMENTAR=AlmaRole(alma_id="2", alma_name="Generic", selection_rationale="LOW", score=0.4), # TRIGGER
        ANTAGONISTA=AntagonistRole(alma_id="3", alma_name="Generic", selection_rationale="LOW", score=0.3), # TRIGGER
        METODOLOGICA=AlmaRole(alma_id="4", alma_name="Generic", selection_rationale="LOW", score=0.5) # TRIGGER
    )

    # 3. Setup Mocks for Services
    with patch("app.agents.graph_factory.select_panel", AsyncMock(return_value=low_score_panel)), \
         patch("app.agents.graph_factory.genesis_service.generate_alma", AsyncMock(return_value={
             "name": "Foucault Ressuscitado",
             "system_prompt": "Lexico X...",
             "id": "gen_1"
         })) as mock_genesis, \
         patch("app.agents.graph_factory.debate_subgraph.ainvoke", AsyncMock(return_value={"synthesis": "done", "turns": []})):

        # 4. Execute Node
        await debate_node(state)

        # 5. Verify Genesis was called for the 3 low-score roles
        assert mock_genesis.call_count == 3
        print("TDD: Genesis fallback verified for score < 0.8")

@pytest.mark.asyncio
async def test_debate_node_normal_flow_high_adherence():
    """
    TDD: Test Case 1 (Normal Flow)
    Ensure that when scores are > 0.8, Genesis is NOT callled.
    """
    state = BackendState(
        messages=[],
        project_id="test_proj",
        user_id="test_user",
        active_soul_ids=["user_alma_1", "user_alma_2", "user_alma_3"],
        canvas_nodes=[],
        is_debate_mode=True
    )

    high_score_panel = SelectedPanel(
        PRIMARIA=AlmaRole(alma_id="1", alma_name="A", selection_rationale="H", score=0.95),
        COMPLEMENTAR=AlmaRole(alma_id="2", alma_name="B", selection_rationale="H", score=0.85),
        ANTAGONISTA=AntagonistRole(alma_id="3", alma_name="C", selection_rationale="H", score=0.9),
        METODOLOGICA=AlmaRole(alma_id="4", alma_name="D", selection_rationale="H", score=0.81)
    )

    with patch("app.agents.graph_factory.select_panel", AsyncMock(return_value=high_score_panel)), \
         patch("app.agents.graph_factory.genesis_service.generate_alma", AsyncMock()) as mock_genesis, \
         patch("app.agents.graph_factory.debate_subgraph.ainvoke", AsyncMock(return_value={"synthesis": "done", "turns": []})):

        await debate_node(state)

        # Genesis should NOT be called
        assert mock_genesis.call_count == 0
        print("TDD: Normal flow verified (No Genesis for high adherence)")
