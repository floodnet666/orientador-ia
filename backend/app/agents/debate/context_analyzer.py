"""
ContextAnalyzer — classifies the user message into a debate_intent.
Uses qwen3.5:0.8b for fast JSON classification.
"""
import json
import logging
import re
from json_repair import repair_json
from typing import Literal, Optional, Any


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
    model=settings.OLLAMA_ORCHESTRATOR_MODEL,
    system_prompt=CONTEXT_ANALYZER_PROMPT,
    output_schema=IntentOutput
)


async def analyze_context(state: Any, user_message: str) -> DebateContext:
    """Classify the user message into a DebateContext."""
    import time
    t0 = time.perf_counter()
    
    def _extract_json_robust(text: str) -> str:
        """Extracts the largest JSON object from a text using a brace-stack counter."""
        import re
        # Primeiro, remove possíveis blocos markdown ```json
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        start = text.find('{')
        if start == -1:
            return ""
        
        stack = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    return text[start:i+1]
        return ""

    # Helpers para extrair dados independentemente do tipo de state (Pydantic ou TypedDict)
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    current_canvas = _get(state, "current_canvas")
    project_id = _get(state, "project_id", "default_project")
    academic_level = _get(state, "academic_level", "BACHELORS")
    round_number = _get(state, "debate_round_number", 0)
    # previous_debate_summary pode vir como dict ou str no state
    prev_summary = _get(state, "previous_debate_summary")
    if isinstance(prev_summary, dict):
        prev_summary = json.dumps(prev_summary, ensure_ascii=False)

    def _val(field) -> str:
        if isinstance(field, dict):
            return field.get("content", "").strip()
        # Se for um objeto Pydantic (como nos campos de CanvasState)
        if hasattr(field, "content"):
            return getattr(field, "content", "").strip()
        return str(field).strip() if field else ""

    canvas_snapshot = {
        "tema": _val(_get(current_canvas, "tema")),
        "problema": _val(_get(current_canvas, "problema")),
        "justificativa": _val(_get(current_canvas, "justificativa")),
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
                # [V9.1.7] Extrator robusto para isolar JSON de poluição textual
                json_str = _extract_json_robust(result)
                if not json_str:
                    json_str = repair_json(result) # Fallback para o texto inteiro se não achar {
                
                # Sanitização anti-caracteres-de-controle
                json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
                
                if not json_str or json_str == "{}":
                    log.warning("[DEBATE] Extraction/Repair returned empty/invalid: %s", json_str)
                    raise ValueError("Failed to extract valid JSON from LLM output")
                
                analysis = IntentOutput.model_validate_json(json_str)
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
        intent = "FREE_DEBATE" # Fallback de segurança

    log.info("[DEBATE] ContextAnalyzer: intent=%s in %.2fs", intent, time.perf_counter() - t0)

    # Reconstrução do canvas como dict puro para o DebateContext
    def _to_dict(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, dict):
            return obj
        return {}

    return DebateContext(
        project_id=project_id,
        canvas={
            "tema": {"content": _val(_get(current_canvas, "tema"))},
            "problema": {"content": _val(_get(current_canvas, "problema"))},
            "justificativa": {"content": _val(_get(current_canvas, "justificativa"))},
            "objetivos": _to_dict(_get(current_canvas, "objetivos")),
            "metodologia": _to_dict(_get(current_canvas, "metodologia")),
        },
        user_message=user_message,
        debate_intent=intent,  # type: ignore[arg-type]
        academic_level=academic_level,
        round_number=round_number,
        previous_debate_summary=prev_summary,
    )
