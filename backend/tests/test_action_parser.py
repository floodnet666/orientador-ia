import json
import pytest
from app.services.action_parser import parse_action_stream, parse_action_stream_async
from app.models.action_token import ActionToken

def stream_from(text: str):
    """Simula stream chunk a chunk (1 char por vez — pior caso)."""
    for ch in text:
        yield ch

def collect(gen):
    return list(gen)

def test_pure_text_passthrough():
    """Texto sem tokens deve passar inalterado."""
    text = "Olá, este é um texto normal sem tokens."
    events = collect(parse_action_stream(stream_from(text)))
    result = "".join(e["data"] for e in events if e["event"] == "text")
    assert result == text
    assert all(e["event"] == "text" for e in events)

def test_single_action_token_extracted():
    """Um único token de acção deve ser extraído correctamente."""
    text = 'Veja o parágrafo `[ACTION:{"type":"SPOTLIGHT_PDF","payload":{"section_ref":"§2.3"}}]` aqui.'
    events = collect(parse_action_stream(stream_from(text)))
    action_events = [e for e in events if e["event"] == "action"]
    text_events   = [e for e in events if e["event"] == "text"]
    assert len(action_events) == 1
    assert action_events[0]["data"].type.value == "SPOTLIGHT_PDF"
    full_text = "".join(e["data"] for e in text_events)
    assert "Veja o parágrafo" in full_text
    assert "aqui." in full_text
    assert "`[ACTION:" not in full_text  # delimitadores não devem vazar

def test_token_split_across_chunks():
    """Token partido em vários chunks deve ser correctamente remontado."""
    full = '`[ACTION:{"type":"CANVAS_NODE","payload":{"id":"n1","label":"Habitus","concept_type":"concept","source_alma":"PB"}}]`'
    chunks = [full[i:i+3] for i in range(0, len(full), 3)]  # chunks de 3 chars
    events = collect(parse_action_stream(iter(chunks)))
    action_events = [e for e in events if e["event"] == "action"]
    assert len(action_events) == 1
    assert action_events[0]["data"].type.value == "CANVAS_NODE"

def test_malformed_token_emitted_as_text():
    """Token malformado (JSON inválido irrecuperável) não deve quebrar o stream."""
    text = 'texto `[ACTION:{{broken json]` continua'
    events = collect(parse_action_stream(stream_from(text)))
    texts = "".join(e["data"] for e in events if e["event"] == "text")
    assert "texto" in texts
    assert "continua" in texts

def test_multiple_tokens_in_stream():
    """Múltiplos tokens no mesmo stream devem todos ser extraídos."""
    text = (
        'Primeiro `[ACTION:{"type":"SPOTLIGHT_PDF","payload":{"section_ref":"§1"}}]` '
        'e depois `[ACTION:{"type":"CONFLICT_FLAG","payload":{"alma_a":"PB","alma_b":"MF","dimension":"x","summary":"y"}}]` fim.'
    )
    events = collect(parse_action_stream(stream_from(text)))
    action_events = [e for e in events if e["event"] == "action"]
    assert len(action_events) == 2
    assert action_events[0]["data"].type.value == "SPOTLIGHT_PDF"
    assert action_events[1]["data"].type.value == "CONFLICT_FLAG"

def test_no_stream_blocking():
    """O parser não deve acumular mais de MAX_TOKEN_BUFFER_CHARS sem emitir."""
    open_token = "`[ACTION:" + "x" * 600  # 600 > MAX_TOKEN_BUFFER_CHARS=512
    events = collect(parse_action_stream(iter([open_token])))
    text_events = [e for e in events if e["event"] == "text"]
    assert len(text_events) > 0  # algo deve ter sido emitido


# ─── Async Tests ──────────────────────────────────────────────────────────────

async def async_stream_from(text: str):
    for ch in text:
        yield ch

@pytest.mark.asyncio
async def test_async_single_action_token_extracted():
    """Versão async: Um único token de acção deve ser extraído correctamente."""
    text = 'Veja `[ACTION:{"type":"SPOTLIGHT_PDF","payload":{"section_ref":"§2.3"}}]` aqui.'
    
    events = []
    async for e in parse_action_stream_async(async_stream_from(text)):
        events.append(e)
        
    action_events = [e for e in events if e["event"] == "action"]
    text_events   = [e for e in events if e["event"] == "text"]
    
    assert len(action_events) == 1
    assert action_events[0]["data"].type.value == "SPOTLIGHT_PDF"
    
    full_text = "".join(e["data"] for e in text_events)
    assert "Veja" in full_text
    assert "aqui." in full_text
    assert "`[ACTION:" not in full_text
