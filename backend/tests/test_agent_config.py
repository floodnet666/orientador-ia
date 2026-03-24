def test_presets_load_without_error():
    from app.models.agent_config import ALMA_PRESETS
    assert "PB" in ALMA_PRESETS
    assert "MF" in ALMA_PRESETS
    assert "PF" in ALMA_PRESETS

def test_preset_has_required_fields():
    from app.models.agent_config import ALMA_PRESETS
    pb = ALMA_PRESETS["PB"]
    assert pb.system_prompt
    assert pb.name
    assert len(pb.action_permissions) > 0

def test_custom_agent_config_valid():
    from app.models.agent_config import AgentConfig, LLMParams
    custom = AgentConfig(
        id="SA",
        name="Spivak",
        persona_description="Teoria pós-colonial",
        system_prompt="...",
        epistemological_stance="Desconstrução",
        conflict_patterns=[]
    )
    assert custom.id == "SA"
    assert custom.llm_params.model == "qwen3.5:1.5b"
