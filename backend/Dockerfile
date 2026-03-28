FROM python:3.12-slim

# Instalar UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Instalar dependências via UV (sem criar venv, instala no sistema)
RUN uv sync --frozen --no-dev

COPY app/ ./app/
COPY scripts/ ./scripts/

CMD ["sh", "-c", "uv run python scripts/healthcheck_rag.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
