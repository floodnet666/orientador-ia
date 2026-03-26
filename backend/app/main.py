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

class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            # Bypassa WebSockets e rotas não-API para evitar quebras no call_next (Starlette issue)
            return await self.app(scope, receive, send)

        start_time = time.perf_counter()
        status_code = [200]
        error_msg = None

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code[0] = 500
            error_msg = str(e)
            raise e
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                async with AsyncSessionLocal() as db:
                    # O middleware ASGI não monta o Request da mesma forma, pegamos do scope
                    # O ID do usuário geralmente entra no scope pelo AuthMiddleware se houver
                    metric = SystemMetric(
                        endpoint=scope["path"],
                        duration_ms=duration_ms,
                        status_code=status_code[0],
                        error_message=error_msg,
                        user_id=None # Simplificado para evitar quebras de contexto stateless
                    )
                    db.add(metric)
                    await db.commit()
                    if duration_ms > 40000:
                        logger.warning(f"SLOW REQUEST DETECTED: {scope['path']} took {duration_ms}ms")
            except Exception as log_err:
                logger.error(f"Failed to save metric: {log_err}")

app.add_middleware(ObservabilityMiddleware)

origins_list = settings.ALLOWED_ORIGINS.split(",")
# Garantir que localhost:3000 esteja sempre presente para desenvolvimento local
base_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"]
for o in origins_list:
    if o and o not in base_origins:
        base_origins.append(o)

allow_origins = [o for o in base_origins if "*" not in o]
regex_list = [o.replace(".", "\\.").replace("*", ".*") for o in base_origins if "*" in o]
allow_origin_regex = f"^({'|'.join(regex_list)})$" if regex_list else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
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
    from app.services.qdrant_service import ensure_almas_collection, ensure_empirical_collection_v2

    try:
        await ensure_almas_collection()
        await ensure_empirical_collection_v2()
        logger.info("Qdrant collections (almas + empirical_v2): OK")
    except Exception as e:
        logger.warning(f"Qdrant not available at startup: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orientador-ia-backend"}
