"""
Extractor de PDF para Markdown estruturado.
Usa pymupdf4llm (wrapper do fitz/PyMuPDF já instalado).

Output: lista de chunks com metadados de posição preservados.
Substitui a lógica de extracção raw de texto do pipeline existente.
NÃO altera o qdrant_service nem o adk.py — apenas o passo de extracção.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pymupdf4llm
import fitz  # PyMuPDF — já instalado


@dataclass
class MarkdownChunk:
    """Unidade de texto pronta para vectorização."""
    chunk_id: str               # ex: "doc_abc123_sec2_chunk4"
    doc_id: str                 # ID do documento pai
    text_raw: str               # texto original do chunk
    text_enriched: str          # texto com contexto injectado (preenchido em M2)
    section_title: str          # título da secção mais próxima
    section_ref: str            # ex: "§2.3" ou "Secção 2.3"
    page_number: int            # página 0-indexed
    bbox: dict                  # {"page": int, "x0": f, "y0": f, "x1": f, "y1": f}
    chunk_index: int            # posição sequencial no documento
    adjacent_chunk_ids: list[str] = field(default_factory=list)


def extract_markdown_chunks(
    pdf_path: str,
    doc_id: str,
    target_chunk_words: int = 300,
    overlap_sentences: int = 1,
) -> list[MarkdownChunk]:
    """
    Extrai e chunka um PDF em MarkdownChunks com metadados de posição.

    Args:
        pdf_path: caminho absoluto para o PDF
        doc_id: identificador único do documento (para prefixar chunk_ids)
        target_chunk_words: tamanho alvo de cada chunk em palavras (~300 = ~1800 chars)
        overlap_sentences: frases sobrepostas entre chunks consecutivos

    Returns:
        Lista ordenada de MarkdownChunks prontos para enriquecimento (M2)
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    # 1. Extrai Markdown com metadados de posição por página
    md_with_meta = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,   # retorna lista por página, não string única
        margins=(0, 0, 0, 0),
    )

    chunks: list[MarkdownChunk] = []
    chunk_index = 0
    current_section = "Introdução"
    current_section_ref = "§0"

    for page_data in md_with_meta:
        page_num = page_data.get("metadata", {}).get("page", 0)
        page_text = page_data.get("text", "")

        # Detecta secções nesta página
        for line in page_text.split("\n"):
            section_match = re.match(r'^#{1,3}\s+(.*)', line)
            if section_match:
                current_section = section_match.group(1).strip()
                # Tenta extrair referência §N.N do título
                ref_match = re.search(r'§\s*(\d+(?:\.\d+)*)', current_section)
                num_match  = re.search(r'^(\d+(?:\.\d+)+)\s', current_section)
                if ref_match:
                    current_section_ref = f"§{ref_match.group(1)}"
                elif num_match:
                    current_section_ref = f"§{num_match.group(1)}"

        # Chunka por palavras, respeitando parágrafos
        page_chunks = _chunk_text_by_words(
            page_text, target_chunk_words, overlap_sentences
        )

        for chunk_text in page_chunks:
            if not chunk_text.strip() or len(chunk_text.split()) < 10:
                continue  # ignora chunks muito pequenos

            chunk_id = f"{doc_id}_p{page_num}_c{chunk_index}"
            chunks.append(MarkdownChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text_raw=chunk_text.strip(),
                text_enriched=chunk_text.strip(),  # será substituído em M2
                section_title=current_section,
                section_ref=current_section_ref,
                page_number=page_num,
                bbox={"page": page_num, "x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0},
                chunk_index=chunk_index,
            ))
            chunk_index += 1

    # Preenche adjacências
    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk.adjacent_chunk_ids.append(chunks[i - 1].chunk_id)
        if i < len(chunks) - 1:
            chunk.adjacent_chunk_ids.append(chunks[i + 1].chunk_id)

    return chunks


def _chunk_text_by_words(
    text: str,
    target_words: int,
    overlap_sentences: int,
) -> list[str]:
    """
    Divide texto em chunks de ~target_words palavras,
    respeitando limites de parágrafo.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > target_words and current:
            chunks.append("\n\n".join(current))
            # Overlap: mantém último(s) parágrafo(s) para contexto
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_words = sum(len(p.split()) for p in current)
        current.append(para)
        current_words += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def get_pdf_global_summary_prompt(md_sample: str) -> str:
    """
    Retorna o prompt para o Ollama gerar um resumo global do documento.
    Usa apenas as primeiras ~500 palavras (suficiente para título, abstract, índice).
    """
    sample = " ".join(md_sample.split()[:500])
    return (
        f"Resume em máximo 2 frases o tema e objectivo principal deste documento académico. "
        f"Responde APENAS com o resumo, sem introdução nem formatação.\n\n{sample}"
    )
