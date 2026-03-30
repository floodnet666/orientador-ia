"""
Canvas Extractor Agent — runs in background after each chat turn.
Analyses conversation and extracts concluded Canvas fields.
"""
import json

from app.config import settings
from app.services.ollama_client import ollama_client
from app.state.graph_state import GraphState


CANVAS_EXTRACTOR_PROMPT = """
Analisar o histórico de chat fornecido e identificar se o utilizador expressou conclusões
claras sobre algum dos seguintes campos do Canvas de Investigação:

- tema: O tema central do trabalho
- problema: A questão/problema de investigação central
- justificativa: A relevância/justificação do estudo
- objetivos_geral: O objectivo geral do estudo
- objetivos_especificos: Lista de objectivos específicos
- metodologia_tipo: Tipo de metodologia (qualitativa/quantitativa/mista)
- metodologia_instrumentos: Lista de instrumentos/técnicas de recolha de dados

Extrair APENAS o que foi explicitamente afirmado pelo utilizador (role='user').
Ignorar perguntas e reflexões. Só extrair certezas.

Responder EXCLUSIVAMENTE com JSON:
{
  "fields_updated": {
    "tema": "<texto ou null>",
    "problema": "<texto ou null>",
    "justificativa": "<texto ou null>",
    "objetivos_geral": "<texto ou null>",
    "objetivos_especificos": ["<item1>", ...] or null,
    "metodologia_tipo": "<texto ou null>",
    "metodologia_instrumentos": ["<item1>", ...] or null
  }
}
"""


async def extract_canvas_fields(state: GraphState) -> dict:
    """Returns dict of fields extracted from conversation. Empty if nothing found."""
    import re
    # 1. Deterministic extraction (fast & cheap)
    extracted_via_regex = {}
    signal_pattern = re.compile(r"<canvas_signal\s+field=['\"]([^'\"]+)['\"]\s+value=['\"]([^'\"]+)['\"]\s*(?:/>|></canvas_signal>)", re.IGNORECASE)
    
    messages = state.get("messages", [])
    last_msg = next((m for m in reversed(messages) if m.type == "ai"), None)
    if last_msg:
        for match in signal_pattern.finditer(last_msg.content):
            field = match.group(1).strip()
            value = match.group(2).strip()
            extracted_via_regex[field] = value
            
    if extracted_via_regex:
        return extracted_via_regex

    # 2. LLM extraction (fallback for natural language)
    messages = state.get("messages", [])
    history_text = ""
    for msg in messages[-15:]:
        role = "user" if msg.type == "human" else "assistant"
        content = msg.content
        history_text += f"[{role}]: {content}\n"

    try:
        response = await ollama_client.chat_complete(
            model=settings.OLLAMA_ORCHESTRATOR_MODEL,
            messages=[{"role": "user", "content": history_text}],
            system=(
                CANVAS_EXTRACTOR_PROMPT + 
                "\nINSTRUÇÃO ADICIONAL: Extraia também as conclusões ou resumos estruturados "
                "propostos pelo Assistant, quando estes refinam o progresso da investigação."
            ),
        )
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return data.get("fields_updated", {})
    except Exception:
        pass
    return {}
