import asyncio
import os
import uuid
import logging
from pathlib import Path

# Configura logs
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag_verify")

async def verify_pipeline():
    from app.services.empirical.document_processor import empirical_processor
    from app.services.qdrant_service import get_qdrant, EMPIRICAL_COLLECTION
    
    project_id = uuid.uuid4()
    filename = "artigo_teste_rag_v2.pdf"
    
    # 1. Cria PDF temporário para teste
    import fitz
    pdf_path = "test_rag_v2.pdf"
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "# O Conceito de Habitus em Bourdieu\n\n"
        "O habitus é um sistema de disposições duráveis e transponíveis que funciona "
        "como princípio gerador e organizador de práticas e representações.\n\n"
        "## Secção 2: Estruturas Sociais\n\n"
        "As estruturas incorporadas tornam-se natureza biológica nas práticas sociais."
    )
    page.insert_text((50, 50), content, fontsize=11)
    doc.save(pdf_path)
    doc.close()
    
    try:
        log.info("Iniciando processamento v2.1.0...")
        # 2. Executa pipeline completo
        await empirical_processor.process_pdf_v2(pdf_path, project_id, filename)
        
        # 3. Verifica busca híbrida
        log.info("Testando busca híbrida...")
        results = await empirical_processor.search_evidence(project_id, "O que é habitus?")
        
        if results:
            log.info("SUCESSO: Resultados encontrados!")
            for r in results:
                log.info(f"Score: {r['score']:.4f} | Trecho: {r['text'][:100]}...")
                log.info(f"Contexto: {r['context'][:100]}...")
        else:
            log.error("FALHA: Nenhum resultado retornado.")
            
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

if __name__ == "__main__":
    # Garante que o app está no path
    import sys
    sys.path.append(os.getcwd())
    asyncio.run(verify_pipeline())
