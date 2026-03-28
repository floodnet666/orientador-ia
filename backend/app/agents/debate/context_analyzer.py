"""
ContextAnalyzer — classifies the user message into a debate_intent.
Uses qwen3.5:0.8b for fast JSON classification.
"""
import json
import logging
from json_repair import repair_json
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
    ] = "FREE_DEBATE"
    tema: Optional[str] = None
    objetivo: Optional[str] = None

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
You are a debate intent classifier. Read the user message and classify the debate intent.

Classification rules:
- Message about "justificativa" or "justification" → DEVELOP_JUSTIFICATIVA
- Message about "problema" or "problem" or "research question" → DEVELOP_PROBLEMA
- Message about "objectivos" or "objectives" or "goals" → DEVELOP_OBJETIVOS
- Message about "metodologia" or "methodology" or "method" → DEVELOP_METODOLOGIA
- Any other topic, question, or debate → FREE_DEBATE

CRITICAL: Respond ONLY with a valid JSON object. No explanation. No other text. English only.
Example output:
{"debate_intent": "FREE_DEBATE", "tema": "topic here", "objetivo": null}
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

        if isinstance(result, IntentOutput):
            intent = result.debate_intent
        elif isinstance(result, str):
            log.debug("[DEBATE] ContextAnalyzer raw result: %s", result)
            try:
                # Try to extract and repair JSON
                repaired = repair_json(result)
                if not repaired or repaired == "{}":
                    log.warning("[DEBATE] json_repair returned empty/invalid: %s", repaired)
                    raise ValueError("json_repair returned empty string")
                
                analysis = IntentOutput.model_validate_json(repaired)
                intent = analysis.debate_intent
            except Exception as exc:
                # Manual fallback: try to find intent name in raw text
                log.info("[DEBATE] json_repair failed or no JSON, content: %s", result)
                valid_intents = ["DEVELOP_JUSTIFICATIVA", "DEVELOP_PROBLEMA", "DEVELOP_OBJETIVOS", "DEVELOP_METODOLOGIA", "FREE_DEBATE"]
                for intent_name in valid_intents:
                    if intent_name in result.upper():
                        intent = intent_name
                        break
                else:
                    log.error("[DEBATE] ContextAnalyzer FAILED parsing: %s | Content: %s", exc, result)
                    raise ValueError(f"ContextAnalyzer failed to produce valid JSON or intent: {exc}")
        else:
            raise ValueError(f"ContextAnalyzer returned unexpected type: {type(result)}")
    except Exception as exc:
        log.error("ContextAnalyzer CRITICAL FAILURE: %s", exc)
        raise exc

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
