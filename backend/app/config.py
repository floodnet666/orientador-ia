from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file: app/config.py → app/ → backend/ → orientador-ia/.env
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000"

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:7b"
    OLLAMA_ORCHESTRATOR_MODEL: str = "qwen2.5:7b"
    OLLAMA_GUARDRAIL_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text:latest"
    OLLAMA_EMBED_DIMENSIONS: int = 768
    OLLAMA_NUM_CTX: int = 8192

    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_base"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
