import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def make_chunk(idx: int):
    from app.services.pdf_markdown_extractor import MarkdownChunk
    return MarkdownChunk(
        chunk_id=f"doc1_p0_c{idx}",
        doc_id="doc1",
        text_raw=f"Texto do parágrafo {idx} sobre habitus e campo social.",
        text_enriched="",
        section_title="Referencial Teórico",
        section_ref="§2.3",
        page_number=0,
        bbox={"page": 0, "x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0},
        chunk_index=idx,
    )


@pytest.fixture
def mock_ollama_response():
    """Mock de resposta do Ollama para testes sem servidor."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"response": "Parágrafo sobre estruturas sociais digitais"}
    return mock_resp


def test_enriched_text_contains_all_sections(mock_ollama_response):
    """text_enriched deve conter DOC, SEC, CONTEXTO e o texto original."""
    from app.services.contextual_enricher import enrich_chunks_with_context
    chunks = [make_chunk(0)]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_ollama_response
        result = asyncio.run(
            enrich_chunks_with_context(chunks, "Tese sobre habitus digital.")
        )

    enriched = result[0].text_enriched
    assert "[DOC:" in enriched
    assert "[SEC:" in enriched
    assert "[CONTEXTO:" in enriched
    assert chunks[0].text_raw in enriched


def test_original_text_unchanged(mock_ollama_response):
    """text_raw não deve ser modificado."""
    from app.services.contextual_enricher import enrich_chunks_with_context
    chunk = make_chunk(0)
    original_raw = chunk.text_raw

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_ollama_response
        result = asyncio.run(enrich_chunks_with_context([chunk], "Resumo."))

    assert result[0].text_raw == original_raw


def test_ollama_timeout_uses_fallback():
    """Se o Ollama falhar (timeout), usa fallback sem lançar excepção."""
    import httpx
    from app.services.contextual_enricher import enrich_chunks_with_context
    chunk = make_chunk(0)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("timeout")
        # Não deve lançar excepção
        result = asyncio.run(enrich_chunks_with_context([chunk], "Resumo."))

    assert result[0].text_enriched  # deve ter algum conteúdo (fallback)
    assert "Referencial Teórico" in result[0].text_enriched  # fallback usa section_title


def test_semaphore_prevents_parallel_calls(mock_ollama_response):
    """Verifica que as chamadas são serializadas (semáforo limita a 1)."""
    from app.services.contextual_enricher import enrich_chunks_with_context
    chunks = [make_chunk(i) for i in range(3)]
    call_times = []

    async def mock_post(*args, **kwargs):
        call_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.05)  # simula latência do Ollama
        return mock_ollama_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
        asyncio.run(enrich_chunks_with_context(chunks, "Resumo."))

    # Com semáforo(1), cada chamada começa depois da anterior terminar
    for i in range(1, len(call_times)):
        gap = call_times[i] - call_times[i - 1]
        assert gap >= 0.04, (
            f"Chamadas paralelas detectadas! Gap entre chamada {i-1} e {i}: {gap:.3f}s"
        )


def test_progress_callback_called():
    """O callback de progresso deve ser chamado para cada chunk."""
    from app.services.contextual_enricher import enrich_chunks_with_context
    chunks = [make_chunk(i) for i in range(3)]
    progress_calls = []

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"response": "contexto"})
        )
        asyncio.run(enrich_chunks_with_context(
            chunks, "Resumo.",
            progress_callback=lambda i, t: progress_calls.append((i, t))
        ))

    assert len(progress_calls) == 3
    assert progress_calls[-1] == (3, 3)
