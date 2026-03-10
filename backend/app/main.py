"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import auth, chat, projects, admin
import time
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.sql_models import SystemMetric

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

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        status_code = 200 # Default to 200 OK
        error_msg = None
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error_msg = str(e)
            raise e
        finally:
            # Aqui gravamos a métrica no DB
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if request.url.path.startswith("/api/"):
                try:
                    async with AsyncSessionLocal() as db:
                        # Check if user_id is in request (if authenticated)
                        user_id = getattr(request.state, "user_id", None)
                        metric = SystemMetric(
                            endpoint=request.url.path,
                            duration_ms=duration_ms,
                            status_code=status_code,
                            error_message=error_msg,
                            user_id=user_id
                        )
                        db.add(metric)
                        await db.commit()
                        if duration_ms > 40000:
                            logger.warning(f"SLOW REQUEST DETECTED: {request.url.path} took {duration_ms}ms")
                except Exception as log_err:
                    logger.error(f"Failed to save metric: {log_err}")
        return response

app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import auth, chat, projects, empirical, almas, admin

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(empirical.router)
app.include_router(almas.router)
app.include_router(admin.router)


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
