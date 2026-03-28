import asyncio
import os
import sys
import logging
from uuid import uuid4, UUID

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.empirical.document_processor import empirical_processor
from app.services.genesis_service import genesis_service
from app.services.qdrant_service import index_alma, get_qdrant, ALMAS_COLLECTION
from unittest.mock import AsyncMock

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest-v3")

async def run_setup():
    project_id = UUID("00000000-0000-0000-0000-000000000003") # Fixed for Test 03
    pdf_path = "/docs/artigo -a.pdf" # Path inside container
    
    if not os.path.exists(pdf_path):
        # Local path for dev if not in container?
        # Actually assuming docker exec, so /docs/ is mapped?
        # Let's check where the file is in the container.
        # User said @[d:\orientador.ia\docs\artigo -a.pdf]
        # In docker compose, usually d:\orientador.ia is mounted at /app or /orientador.ia
        # Let's try to locate it.
        alt_path = "/app/docs/artigo -a.pdf"
        if os.path.exists(alt_path):
            pdf_path = alt_path
        else:
            logger.error(f"Ficheiro não encontrado: {pdf_path}")
            return

    # 1. RAG INGESTION
    logger.info(f"🚀 Ingestão RAG: Processando {pdf_path} para o projeto {project_id}")
    await empirical_processor.process_pdf_v2(pdf_path, project_id, "artigo-a.pdf")
    logger.info("✅ RAG Ingested.")

    # 2. GENESIS OF PERTINENT ALMAS
    almas_to_create = [
        "Maziar Raissi, autor principal do artigo sobre PINNs. Defensor fervoroso da integração de leis físicas em Deep Learning.",
        "Boris Galerkin, matemático clássico focado em métodos de resíduos ponderados e elementos finitos. Cético em relação a modelos caixa-preta.",
        "Engenheiro de Simulação CFD experiente, pragmático, focado em custo computacional e fidelidade física em aplicações industriais."
    ]
    
    created_almas = []
    logger.info("🧬 Iniciando Gênese de Almas Acadêmicas...")
    for desc in almas_to_create:
        try:
            alma_data = await genesis_service.generate_alma(desc)
            # Add a fake ID for indexing
            alma_data["id"] = uuid4()
            alma_data["is_approved"] = True
            created_almas.append(alma_data)
            logger.info(f" -> Alma '{alma_data['name']}' criada com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao criar alma para '{desc}': {e}")

    # 3. INDEX ALMAS IN QDRANT
    logger.info("📡 Indexando Almas Técnicas no Qdrant...")
    from types import SimpleNamespace
    for a in created_almas:
        # Create a simple object that index_alma expects
        alma_obj = SimpleNamespace(
            id=a["id"],
            name=a["name"],
            alma_type=a["type"],
            system_prompt=a["system_prompt"],
            description=a["description"],
            is_approved=True
        )
        await index_alma(alma_obj)
    
    logger.info("✨ Setup Concluído para Teste 03.")
    logger.info(f"ID do Projeto: {project_id}")
    logger.info(f"Almas Criadas: {[a['name'] for a in created_almas]}")

if __name__ == "__main__":
    asyncio.run(run_setup())
