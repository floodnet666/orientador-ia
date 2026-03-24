from app.models.action_token import ActionToken, ActionType, SpotlightPayload

def test_action_type_enum_completeness():
    """Garante que todos os ActionType têm representação string correcta."""
    for at in ActionType:
        assert isinstance(at.value, str)
        assert at.value == at.value.upper()

def test_spotlight_payload_valid():
    p = SpotlightPayload(section_ref="§2.3", keyword="habitus")
    assert p.section_ref == "§2.3"

def test_action_token_serialization():
    t = ActionToken(type=ActionType.SPOTLIGHT_PDF, payload={"section_ref": "§2.3"})
    d = t.model_dump()
    assert d["type"] == "SPOTLIGHT_PDF"
