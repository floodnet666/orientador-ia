"""
Ao carregar um PDF, indexa as secções (por cabeçalhos e §-markers)
e devolve um mapa section_ref -> {page, bbox}.

Usa PyMuPDF (fitz) que já está instalado.
"""
import fitz  # PyMuPDF
import re
from typing import Optional
from pydantic import BaseModel


class SectionLocation(BaseModel):
    page: int           # 0-indexed
    y_top: float        # posição Y normalizada (0-1) no início da secção
    y_bottom: float     # posição Y normalizada (0-1) no final do bloco
    text_snippet: str   # primeiros 100 chars do bloco


class PDFSectionIndex:
    def __init__(self, pdf_path: str):
        self.doc = fitz.open(pdf_path)
        self.index: dict[str, SectionLocation] = {}
        self._build_index()

    def _build_index(self):
        """
        Indexa secções identificadas por:
        - Padrões §N.N (ex: §2.3, §1, §4.2.1)
        - Padrões numéricos de cabeçalho (ex: "2.3 Habitus")
        """
        section_pattern = re.compile(r'§\s*(\d+(?:\.\d+)*)')
        
        for page_num, page in enumerate(self.doc):
            blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text,block_no,type)]
            page_height = page.rect.height
            
            for block in blocks:
                if block[6] != 0:  # type 0 = text
                    continue
                text = block[4].strip()
                if not text:
                    continue
                
                # Procura §-markers
                matches = section_pattern.findall(text)
                for match in matches:
                    ref = f"§{match}"
                    if ref not in self.index:
                        y_top    = block[1] / page_height
                        y_bottom = block[3] / page_height
                        self.index[ref] = SectionLocation(
                            page=page_num,
                            y_top=y_top,
                            y_bottom=y_bottom,
                            text_snippet=text[:100]
                        )

    def locate(self, section_ref: str) -> Optional[SectionLocation]:
        """
        Localiza uma secção por referência.
        Aceita: "§2.3", "2.3", "§2", etc.
        """
        ref = section_ref.strip()
        if not ref.startswith('§'):
            ref = f"§{ref}"
        
        return self.index.get(ref)

    def search_keyword(self, keyword: str, page_hint: Optional[int] = None) -> Optional[SectionLocation]:
        """
        Fallback: procura keyword no texto quando section_ref não está no índice.
        """
        pages_to_search = [page_hint] if page_hint is not None else list(range(len(self.doc)))
        
        for page_num in pages_to_search:
            page = self.doc[page_num]
            blocks = page.get_text("blocks")
            page_height = page.rect.height
            
            for block in blocks:
                if block[6] != 0:
                    continue
                if keyword.lower() in block[4].lower():
                    return SectionLocation(
                        page=page_num,
                        y_top=block[1] / page_height,
                        y_bottom=block[3] / page_height,
                        text_snippet=block[4][:100]
                    )
        return None
