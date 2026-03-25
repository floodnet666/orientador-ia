import pytest
from pathlib import Path


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    """Cria PDF de teste com estrutura real (títulos, parágrafos, tabela)."""
    import fitz
    tmp = tmp_path_factory.mktemp("pdfs")
    pdf_path = str(tmp / "sample.pdf")
    doc = fitz.open()

    page = doc.new_page()
    content = (
        "# 1. Introdução\n\n"
        "Este trabalho analisa o habitus no contexto digital. "
        "A hipótese central é que as plataformas algorítmicas reproduzem estruturas sociais.\n\n"
        "## 1.1 Objetivos\n\n"
        "Identificar mecanismos de reprodução simbólica em plataformas digitais.\n\n"
        "# 2. Referencial Teórico\n\n"
        "## 2.3 Habitus e Campo Digital\n\n"
        "O habitus (Bourdieu, 1989) é definido como sistema de disposições duráveis. "
        "No contexto digital, estas disposições são reforçadas algoritmicamente. "
        "A equação $E = F \\cdot d$ representa o trabalho simbólico acumulado.\n\n"
        "# 3. Metodologia\n\n"
        "Utilizou-se análise de conteúdo qualitativa com corpus de 120 entrevistas."
    )
    page.insert_text((50, 50), content, fontsize=11)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_extraction_returns_chunks(sample_pdf):
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    chunks = extract_markdown_chunks(sample_pdf, doc_id="test_doc")
    assert len(chunks) >= 1, "Deve retornar pelo menos 1 chunk"


def test_chunks_have_required_fields(sample_pdf):
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    chunks = extract_markdown_chunks(sample_pdf, doc_id="test_doc")
    for chunk in chunks:
        assert chunk.chunk_id.startswith("test_doc_")
        assert chunk.doc_id == "test_doc"
        assert isinstance(chunk.text_raw, str) and len(chunk.text_raw) > 0
        assert isinstance(chunk.page_number, int) and chunk.page_number >= 0
        assert "page" in chunk.bbox


def test_chunk_ids_are_unique(sample_pdf):
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    chunks = extract_markdown_chunks(sample_pdf, doc_id="test_doc")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Todos os chunk_ids devem ser únicos"


def test_adjacency_filled(sample_pdf):
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    chunks = extract_markdown_chunks(sample_pdf, doc_id="test_doc")
    if len(chunks) >= 2:
        # O segundo chunk deve ter o primeiro como adjacente
        assert chunks[1].adjacent_chunk_ids[0] == chunks[0].chunk_id


def test_file_not_found_raises():
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    with pytest.raises(FileNotFoundError):
        extract_markdown_chunks("/tmp/nao_existe.pdf", "doc_x")


def test_min_chunk_size_filters_noise(sample_pdf):
    from app.services.pdf_markdown_extractor import extract_markdown_chunks
    chunks = extract_markdown_chunks(sample_pdf, doc_id="test_doc")
    # Nenhum chunk deve ter menos de 10 palavras
    for chunk in chunks:
        assert len(chunk.text_raw.split()) >= 10, (
            f"Chunk muito pequeno: '{chunk.text_raw[:50]}'"
        )
