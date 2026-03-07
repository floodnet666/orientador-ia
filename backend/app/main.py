"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, projects

# Register all Almas at startup
import app.agents.almas.foucault  # noqa: F401
import app.agents.almas.bourdieu  # noqa: F401
import app.agents.almas.freire  # noqa: F401
import app.agents.almas.habermas  # noqa: F401
import app.agents.almas.hooks  # noqa: F401
import app.agents.almas.etnografa  # noqa: F401
import app.agents.almas.estatistico  # noqa: F401
import app.agents.almas.fenomenologa  # noqa: F401
import app.agents.almas.grounded  # noqa: F401
import app.agents.almas.narrativo  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Orientador.IA API",
    description="API REST + WebSocket para plataforma de orientação académica multi-agente",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import auth, chat, projects, empirical, almas

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(empirical.router)
app.include_router(almas.router)


@app.on_event("startup")
async def startup_event():
    from app.config import settings
    from app.services.ollama_client import ollama_client

    logger.info("Orientador.IA starting up...")

    # Verify Ollama models are available
    for model in [settings.OLLAMA_CHAT_MODEL, settings.OLLAMA_GUARDRAIL_MODEL]:
        available = await ollama_client.check_model(model)
        if not available:
            logger.warning(
                f"Model {model} not found in Ollama. Please pull it: "
                f"docker compose exec ollama ollama pull {model}"
            )
        else:
            logger.info(f"Model {model}: OK")

    # Ensure Qdrant collections exist
    from app.services.qdrant_service import ensure_almas_collection

    try:
        await ensure_almas_collection()
        logger.info("Qdrant almas_catalog collection: OK")
    except Exception as e:
        logger.warning(f"Qdrant not available at startup: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orientador-ia-backend"}
