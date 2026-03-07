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
    history_text = "\n".join(
        f"[{msg.role}] {msg.alma_name or ''}: {msg.content}"
        for msg in state.chat_history[-10:]
    )
    try:
        response = await ollama_client.chat_complete(
            model=settings.OLLAMA_ORCHESTRATOR_MODEL,
            messages=[{"role": "user", "content": history_text}],
            system=CANVAS_EXTRACTOR_PROMPT,
        )
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return data.get("fields_updated", {})
    except Exception:
        pass
    return {}
