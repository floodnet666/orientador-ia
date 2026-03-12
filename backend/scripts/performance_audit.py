import asyncio
import time
import json
import logging
from uuid import UUID
from unittest.mock import MagicMock

# Force context for simulation
import os
import sys
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.config import settings
from app.agents.debate.debate_runner import DebateRunner
from app.state.graph_state import GraphState, ChatMessageState, CanvasState

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("audit.llm")

async def performance_audit():
    runner = DebateRunner()
    
    state = GraphState(
        project_id=str(UUID(int=1)),
        user_id="audit_user",
        academic_level="PHD",
        chat_history=[ChatMessageState(role="user", content="Contexto inicial.", timestamp="2024-01-01T00:00:00")],
        current_canvas=CanvasState(tema={"content": "Audit", "is_locked": False}),
        active_theoretical_alma="Theo",
        active_methodological_alma="Meth"
    )

    context = MagicMock()
    context.user_message = "Mensagem de auditoria."
    
    # Setup registry with Mocks that behave like Almas
    alma_registry = {
        "Theo": MagicMock(),
        "Meth": MagicMock(),
        "Anta": MagicMock()
    }
    for name, m in alma_registry.items():
        m.alma_name = name
        m.name = name
        m.system_prompt = f"Prompt for {name}"

    panel = MagicMock()
    panel.PRIMARIA = alma_registry["Theo"]
    panel.COMPLEMENTAR = alma_registry["Meth"]
    panel.ANTAGONISTA = alma_registry["Anta"]

    log.info(f"Starting Performance Audit (num_ctx={settings.OLLAMA_NUM_CTX})...")
    t_start = time.perf_counter()
    
    # We mock the Agent.stream to simulate the LLM's streaming and capture metrics
    from app.agents.debate.debate_runner import Agent
    
    async def mock_agent_stream(self, input_text, context=None):
        t0 = time.perf_counter()
        yield f"Resposta simulada para {self.name}. "
        duration = time.perf_counter() - t0
        log.info(f"Metrica Turno [{self.name}]: TTFT={duration:.4f}s | Prompt Size ~{len(input_text)} chars")

    with patch("app.agents.debate.debate_runner.Agent.stream", mock_agent_stream):
        async for event in runner.run(state, context, panel, alma_registry):
            if event["type"] == "debate_complete":
                 total_duration = time.perf_counter() - t_start
                 log.info(f"Total Pipeline Audit Duration: {total_duration:.4f}s")
                 for role, turn in event["turns"].items():
                     log.info(f"Turno {role}: {len(turn)} chars")

if __name__ == "__main__":
    from unittest.mock import patch
    asyncio.run(performance_audit())
