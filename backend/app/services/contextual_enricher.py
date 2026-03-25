"""
Enriquece MarkdownChunks com contexto situacional via qwen3.5:0.8b.

CRÍTICO: OLLAMA_NUM_PARALLEL=1 no docker-compose.
Usa asyncio.Semaphore(1) para serializar chamadas ao Ollama.
asyncio.gather é usado apenas para estrutura do código — o semáforo
garante que apenas 1 chamada está activa em simultâneo.
"""
from __future__ import annotations

import asyncio
import httpx
from typing import Optional
from app.config import settings
from app.services.pdf_markdown_extractor import MarkdownChunk

# Respeita OLLAMA_NUM_PARALLEL=1
_OLLAMA_SEMAPHORE = asyncio.Semaphore(1)
_OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL.rstrip("/")
# Modelo unificado — evita memory swap
_CONTEXT_MODEL = settings.OLLAMA_CHAT_MODEL

print(f"DEBUG: _OLLAMA_BASE_URL={_OLLAMA_BASE_URL}")
print(f"DEBUG: _CONTEXT_MODEL={_CONTEXT_MODEL}")


async def _generate_situational_context(
    chunk: MarkdownChunk,
    global_summary: str,
    client: httpx.AsyncClient,
    timeout: float = 30.0,
) -> str:
    """
    Gera uma frase de contexto situacional para um chunk.
    Serializado pelo semáforo — máximo 1 chamada simultânea.
    """
    prompt = (
        f"Documento: {global_summary}\n"
        f"Secção actual: {chunk.section_title}\n\n"
        f"Texto do parágrafo:\n{chunk.text_raw[:600]}\n\n"
        "Escreve UMA frase (máximo 25 palavras) que situa este parágrafo "
        "no contexto do documento. Responde APENAS com a frase, sem pontuação final."
    )

    async with _OLLAMA_SEMAPHORE:
        try:
            response = await client.post(
                f"{_OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": _CONTEXT_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,   # determinístico
                        "num_predict": 50,    # máximo 50 tokens
                        "think": False,       # desactiva thinking mode
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except (httpx.TimeoutException, httpx.HTTPError):
            # Fallback gracioso: usa apenas título da secção
            return f"Parágrafo da secção '{chunk.section_title}'"


async def enrich_chunks_with_context(
    chunks: list[MarkdownChunk],
    global_summary: str,
    progress_callback: Optional[callable] = None,
) -> list[MarkdownChunk]:
    """
    Enriquece todos os chunks com contexto situacional.

    O processo é SEQUENCIAL por causa de OLLAMA_NUM_PARALLEL=1.
    Para um PDF de 100 páginas (~300 chunks), espera ~5 minutos.
    Isto é aceitável pois a ingestão é um processo offline, não real-time.

    Args:
        chunks: lista de MarkdownChunks do M1
        global_summary: resumo global do documento (gerado antes)
        progress_callback: função opcional (chunk_index, total) -> None

    Returns:
        Mesmos chunks com text_enriched preenchido
    """
    template = "[DOC: {doc}]\n[SEC: {sec}]\n[CONTEXTO: {ctx}]\n\n{text}"

    async with httpx.AsyncClient() as client:
        for i, chunk in enumerate(chunks):
            ctx = await _generate_situational_context(
                chunk, global_summary, client
            )
            chunk.text_enriched = template.format(
                doc=global_summary[:200],
                sec=chunk.section_title,
                ctx=ctx,
                text=chunk.text_raw,
            )
            if progress_callback:
                progress_callback(i + 1, len(chunks))

    return chunks


async def generate_global_summary(
    md_sample: str,
    timeout: float = 60.0,
) -> str:
    """
    Gera resumo global do documento usando qwen3.5:0.8b.
    Chamado UMA VEZ antes do loop de chunks.
    """
    from app.services.pdf_markdown_extractor import get_pdf_global_summary_prompt
    prompt = get_pdf_global_summary_prompt(md_sample)

    async with _OLLAMA_SEMAPHORE:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{_OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": _CONTEXT_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 80, "think": False},
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.json().get("response", "Documento académico.").strip()
            except (httpx.TimeoutException, httpx.HTTPError):
                return "Documento académico sem resumo disponível."
