import os
import pytest
import fitz  # PyMuPDF

# Cria um PDF de teste mínimo
@pytest.fixture(scope="module")
def test_pdf(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pdfs")
    pdf_path = str(tmp / "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "§2.3 Habitus Digital\n\nO habitus opera como estrutura estruturante.")
    page.insert_text((50, 200), "§3 Foucault e o Poder\n\nO dispositivo de vigilância.")
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_index_builds_without_error(test_pdf):
    from app.services.pdf_section_indexer import PDFSectionIndex
    idx = PDFSectionIndex(test_pdf)
    assert isinstance(idx.index, dict)

def test_locate_section_found(test_pdf):
    from app.services.pdf_section_indexer import PDFSectionIndex
    idx = PDFSectionIndex(test_pdf)
    loc = idx.locate("§2.3")
    assert loc is not None
    assert loc.page == 0

def test_locate_section_not_found_returns_none(test_pdf):
    from app.services.pdf_section_indexer import PDFSectionIndex
    idx = PDFSectionIndex(test_pdf)
    loc = idx.locate("§99.99")
    assert loc is None

def test_locate_without_symbol(test_pdf):
    from app.services.pdf_section_indexer import PDFSectionIndex
    idx = PDFSectionIndex(test_pdf)
    loc = idx.locate("2.3")  # sem §
    assert loc is not None

def test_keyword_search_fallback(test_pdf):
    from app.services.pdf_section_indexer import PDFSectionIndex
    idx = PDFSectionIndex(test_pdf)
    loc = idx.search_keyword("habitus")
    assert loc is not None
    assert "habitus" in loc.text_snippet.lower() or "Habitus" in loc.text_snippet
