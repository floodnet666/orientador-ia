import pytest
from app.services.json_repair import repair_json, try_repair_json

def test_valid_json_unchanged():
    raw = '{"type": "SPOTLIGHT_PDF", "payload": {"section_ref": "§2.3"}}'
    assert repair_json(raw) == raw

def test_trailing_comma_object():
    raw = '{"a": 1, "b": 2,}'
    result = repair_json(raw)
    import json
    assert json.loads(result) == {"a": 1, "b": 2}

def test_trailing_comma_array():
    raw = '[1, 2, 3,]'
    result = repair_json(raw)
    import json
    assert json.loads(result) == [1, 2, 3]

def test_unclosed_object():
    raw = '{"type": "CANVAS_NODE", "payload": {"id": "n1"'
    result = repair_json(raw)
    import json
    parsed = json.loads(result)
    assert parsed["type"] == "CANVAS_NODE"

def test_truncated_stream_value():
    """JSON cortado no meio de um valor string."""
    raw = '{"type": "SPOTLIGHT_PDF", "payload": {"section_ref": "§2'
    result = repair_json(raw)
    import json
    parsed = json.loads(result)
    assert "type" in parsed

def test_single_quotes():
    raw = "{'type': 'CANVAS_NODE', 'payload': {'id': 'n1'}}"
    result = repair_json(raw)
    import json
    parsed = json.loads(result)
    assert parsed["type"] == "CANVAS_NODE"

def test_empty_raises():
    with pytest.raises(ValueError):
        repair_json("")

def test_try_repair_returns_none_on_failure():
    result = try_repair_json("{{{{{{{{{{{{")
    assert result is None

def test_try_repair_returns_dict_on_success():
    result = try_repair_json('{"a": 1}')
    assert result == {"a": 1}

def test_nested_unclosed():
    raw = '{"a": {"b": {"c": 1'
    result = repair_json(raw)
    import json
    parsed = json.loads(result)
    assert parsed["a"]["b"]["c"] == 1
