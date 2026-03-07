from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file: app/config.py → app/ → backend/ → orientador-ia/.env
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3.5:4b"  # 1 - Almas (chat fluido)
    OLLAMA_ORCHESTRATOR_MODEL: str = "qwen3.5:4b"  # 2 - Orchestrator + Canvas (raciocínio estruturado)
    OLLAMA_GUARDRAIL_MODEL: str = "qwen3.5:0.8b"  # 3 - Guardrails (classificação ultra-rápida)
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBED_DIMENSIONS: int = 768

    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_base"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
