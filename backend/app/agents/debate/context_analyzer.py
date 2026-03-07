"""
ContextAnalyzer — classifies the user message into a debate_intent.
Uses qwen3.5:0.8b for fast JSON classification.
"""
import json
import logging
from typing import Literal, Optional

from pydantic import BaseModel

from app.services.ollama_client import ollama_client
from app.config import settings
from app.state.graph_state import GraphState

log = logging.getLogger("debate.context_analyzer")


from app.lib import adk

class IntentOutput(BaseModel):
    debate_intent: Literal[
        "DEVELOP_JUSTIFICATIVA",
        "DEVELOP_PROBLEMA",
        "DEVELOP_OBJETIVOS",
        "DEVELOP_METODOLOGIA",
        "FREE_DEBATE",
    ]

class DebateContext(BaseModel):
    project_id: str
    canvas: dict
    user_message: str
    debate_intent: Literal[
        "DEVELOP_JUSTIFICATIVA",
        "DEVELOP_PROBLEMA",
        "DEVELOP_OBJETIVOS",
        "DEVELOP_METODOLOGIA",
        "FREE_DEBATE",
    ]
    academic_level: str
    round_number: int = 0
    previous_debate_summary: Optional[str] = None

CONTEXT_ANALYZER_PROMPT = """
Analisar a mensagem do utilizador e o estado actual do projecto.
Determinar qual campo do Canvas o utilizador quer desenvolver.

Regras de classificação de debate_intent:
- Mensagem sobre "justificativa" → DEVELOP_JUSTIFICATIVA
- Mensagem sobre "problema" ou "questão" → DEVELOP_PROBLEMA
- Mensagem sobre "objectivos" → DEVELOP_OBJETIVOS
- Mensagem sobre "metodologia" ou "método" → DEVELOP_METODOLOGIA
- Qualquer outra dúvida ou debate → FREE_DEBATE

Responda OBRIGATORIAMENTE em JSON seguindo o schema IntentOutput.
"""

context_analyzer_agent = adk.Agent(
    name='context_analyzer',
    model=f'ollama/{settings.OLLAMA_GUARDRAIL_MODEL}',
    system_prompt=CONTEXT_ANALYZER_PROMPT,
    output_schema=IntentOutput
)


async def analyze_context(state: GraphState, user_message: str) -> DebateContext:
    """Classify the user message into a DebateContext."""
    import time
    t0 = time.perf_counter()

    def _val(field) -> str:
        if isinstance(field, dict):
            return field.get("content", "").strip()
        return str(field).strip() if field else ""

    canvas_snapshot = {
        "tema": _val(state.current_canvas.tema),
        "problema": _val(state.current_canvas.problema),
        "justificativa": _val(state.current_canvas.justificativa),
    }

    prompt = (
        f"Mensagem do utilizador: \"{user_message}\"\n\n"
        f"Canvas actual:\n{json.dumps(canvas_snapshot, ensure_ascii=False)}"
    )

    try:
        result = await context_analyzer_agent.run(prompt)
        intent = result.debate_intent if isinstance(result, IntentOutput) else "FREE_DEBATE"
    except Exception as exc:
        log.warning("ContextAnalyzer failed (%s) — defaulting to FREE_DEBATE", exc)
        intent = "FREE_DEBATE"

    log.info("[DEBATE] ContextAnalyzer: intent=%s in %.2fs", intent, time.perf_counter() - t0)

    return DebateContext(
        project_id=state.project_id,
        canvas={
            "tema": {"content": _val(state.current_canvas.tema)},
            "problema": {"content": _val(state.current_canvas.problema)},
            "justificativa": {"content": _val(state.current_canvas.justificativa)},
            "objetivos": state.current_canvas.objetivos if isinstance(state.current_canvas.objetivos, dict) else {},
            "metodologia": state.current_canvas.metodologia if isinstance(state.current_canvas.metodologia, dict) else {},
        },
        user_message=user_message,
        debate_intent=intent,  # type: ignore[arg-type]
        academic_level=state.academic_level,
        round_number=state.debate_round_number,
        previous_debate_summary=state.previous_debate_summary,
    )
