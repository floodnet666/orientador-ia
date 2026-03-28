"""
DebateOrchestrator — main coordinator for the Ateliê Socrático.
Called by chat.py WebSocket handler when a debate trigger is detected.
"""
import json
import logging
import time
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.debate.context_analyzer import analyze_context
from app.agents.debate.debate_runner import debate_runner
from app.agents.debate.debate_synthesizer import synthesize_debate
from app.agents.debate.panel_selector import select_panel
from app.models.sql_models import EcosystemResource
from app.state.graph_state import GraphState

log = logging.getLogger("debate.orchestrator")

PLAGIARISM_RESPONSE = (
    "Detectei uma tentativa de solicitar que eu produza conteúdo académico directamente. "
    "O meu papel é estimular o teu pensamento crítico — não escrever o trabalho. "
    "Reformula a tua pergunta de forma a pedir reflexão, não produção de texto."
)


class DebateOrchestrator:
    async def run(self, state: GraphState, user_message: str, db: AsyncSession) -> AsyncIterator[dict]:
        """Full debate pipeline. Yields SSE events for the WebSocket."""
        t_total = time.perf_counter()
        req_id = f"debate:{state.project_id}@{int(t_total)}"
        log.info("[%s] START debate pipeline", req_id)

        # ── Step 1: Analyse context ────────────────────────────────────────────
        t1 = time.perf_counter()
        context = await analyze_context(state, user_message)
        log.info("[%s] 1_CONTEXT intent=%s in %.2fs", req_id, context.debate_intent, time.perf_counter() - t1)

        yield {
            "type": "system_status",
            "message": f"A preparar debate sobre: {context.debate_intent.replace('_', ' ').lower()}"
        }

        # ── Step 2: Load Alma registry from DB ────────────────────────────────
        t2 = time.perf_counter()
        result = await db.execute(
            select(EcosystemResource).where(
                EcosystemResource.is_approved == True,  # noqa: E712
            )
        )
        alma_list = result.scalars().all()
        alma_registry = {str(a.id): a for a in alma_list}
        log.info("[%s] 2_LOAD_ALMAS count=%d in %.2fs", req_id, len(alma_list), time.perf_counter() - t2)

        if len(alma_list) < 4:
            log.warning("[%s] Not enough Almas for debate (%d < 4)", req_id, len(alma_list))
            yield {
                "type": "error",
                "message": "Projecto precisa de pelo menos 4 Almas aprovadas para activar o debate."
            }
            return

        # ── Step 3: Select panel ──────────────────────────────────────────────
        t3 = time.perf_counter()
        panel = await select_panel(
            context=context,
            alma_list=alma_list,
            active_theoretical_alma=state.active_theoretical_alma,
            active_methodological_alma=state.active_methodological_alma,
            active_soul_ids=state.active_soul_ids,
        )
        log.info("[%s] 3_PANEL_SELECTED in %.2fs", req_id, time.perf_counter() - t3)

        yield {
            "type": "panel_selected",
            "panel": {
                "PRIMARIA": {
                    "name": panel.PRIMARIA.alma_name,
                    "rationale": panel.PRIMARIA.selection_rationale,
                },
                "COMPLEMENTAR": {
                    "name": panel.COMPLEMENTAR.alma_name,
                    "rationale": panel.COMPLEMENTAR.selection_rationale,
                },
                "ANTAGONISTA": {
                    "name": panel.ANTAGONISTA.alma_name,
                    "angle": panel.ANTAGONISTA.antagonism_angle,
                },
                "METODOLOGICA": {
                    "name": panel.METODOLOGICA.alma_name,
                },
            }
        }

        # ── Step 4: Run debate (4 streaming turns) ────────────────────────────
        t4 = time.perf_counter()
        turns: dict = {}
        async for event in debate_runner.run(state, context, panel, alma_registry):
            yield event
            if event["type"] == "debate_complete":
                turns = event.get("turns", {})
        log.info("[%s] 4_DEBATE_RUNS done in %.2fs", req_id, time.perf_counter() - t4)

        # ── Step 5: Synthesize ────────────────────────────────────────────────
        t5 = time.perf_counter()
        summary = await synthesize_debate(
            turns=turns,
            debate_intent=context.debate_intent,
            canvas=context.canvas,
        )
        log.info("[%s] 5_SYNTHESIZER done in %.2fs", req_id, time.perf_counter() - t5)

        # Canvas update if content is mature enough
        canvas_updates = {k: v for k, v in summary.canvas_updates.items() if v}
        if canvas_updates:
            yield {"type": "canvas_update", "updates": canvas_updates}

        # Final debate question card
        yield {
            "type": "debate_question",
            "tensions": summary.core_tensions,
            "consensus": summary.points_of_consensus,
            "question": summary.question_for_user,
        }

        yield {"type": "done"}

        log.info(
            "[%s] DEBATE COMPLETE total=%.2fs | rounds_so_far=%d",
            req_id, time.perf_counter() - t_total, state.debate_round_number + 1,
        )
