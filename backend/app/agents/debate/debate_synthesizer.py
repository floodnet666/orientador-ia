"""
DebateSynthesizer — produces DebateSummary after all 4 turns complete.
Extracts tensions, consensus, canvas_updates, and final question for user.
"""
import json
import logging
import re
import time
from typing import Optional
from json_repair import repair_json

from pydantic import BaseModel

from app.config import settings
from app.lib import adk

log = logging.getLogger("debate.synthesizer")


class DebateSummary(BaseModel):
    core_tensions: list[str]
    points_of_consensus: list[str]
    canvas_updates: dict  # {field: value | null}
    question_for_user: str


SYNTHESIZER_PROMPT = """
Analisar os 4 turnos do debate e produzir um resumo estruturado.

O que deves produzir:
1. core_tensions: lista de 2-3 tensões intelectuais NÃO resolvidas que emergiram.
2. points_of_consensus: lista de 1-2 pontos onde TODAS as Almas concordaram.
3. canvas_updates: extrair texto específico para {"justificativa": "str", "problema": "str"}.
4. question_for_user: UMA pergunta final que force uma escolha do investigador.

Responda OBRIGATORIAMENTE em JSON puro, sem texto adicional. Schema:
{
  "core_tensions": ["tensão 1", "tensão 2"],
  "points_of_consensus": ["consenso 1"],
  "canvas_updates": {"justificativa": "...", "problema": "..."},
  "question_for_user": "..."
}
"""

debate_synthesizer_agent = adk.Agent(
    name='debate_synthesizer',
    model=f'ollama/{settings.OLLAMA_CHAT_MODEL}',
    system_prompt=SYNTHESIZER_PROMPT,
    output_schema=DebateSummary
)


async def synthesize_debate(
    turns: dict,
    debate_intent: str,
    canvas: dict,
) -> DebateSummary:
    """Produce a DebateSummary from the 4 completed turns."""
    t0 = time.perf_counter()

    transcript = "\n\n".join(
        f"[Turno {i+1} — {role}]\n{content}"
        for i, (role, content) in enumerate(turns.items())
    )

    prompt = (
        f"Campo a desenvolver: {debate_intent}\n"
        f"Canvas: TEMA={canvas.get('tema', {}).get('content', '')} | "
        f"PROBLEMA={canvas.get('problema', {}).get('content', '')}\n\n"
        f"Debate completo:\n{transcript}"
    )

    try:
        summary = await debate_synthesizer_agent.run(prompt)

        if isinstance(summary, DebateSummary):
            log.info("[DEBATE] Synthesizer done in %.2fs | tensions=%d", time.perf_counter() - t0, len(summary.core_tensions))
            return summary

        # If ADK returned a raw string, attempt robust JSON repair
        if isinstance(summary, str):
            try:
                repaired = repair_json(summary)
                if repaired:
                    parsed = DebateSummary.model_validate_json(repaired)
                    log.info("[DEBATE] Synthesizer (repaired parse) done in %.2fs", time.perf_counter() - t0)
                    return parsed
            except Exception as e:
                log.debug("[DEBATE] json_repair failed in synthesizer: %s", e)

        raise ValueError(f"Invalid summary output type: {type(summary)}")

    except Exception as exc:
        log.warning("DebateSynthesizer failed (%s) — returning empty summary", exc)
        return DebateSummary(
            core_tensions=["Tensão entre perspectivas teóricas identificada"],
            points_of_consensus=["Necessidade de fundamentação empírica"],
            canvas_updates={},
            question_for_user="Como pretendes operacionalizar o problema central identificado no debate?",
        )
