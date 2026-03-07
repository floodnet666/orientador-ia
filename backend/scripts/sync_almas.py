import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import EcosystemResource, ResourceTypeEnum
from app.services.ollama_client import ollama_client
from app.services.qdrant_service import ensure_almas_collection, upsert_alma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_almas")

async def sync_almas_to_qdrant():
    logger.info("Starting synchronization of Almas to Qdrant...")
    await ensure_almas_collection()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EcosystemResource).where(EcosystemResource.resource_type == ResourceTypeEnum.ALMA)
        )
        almas = result.scalars().all()
        
        logger.info(f"Found {len(almas)} Almas in SQL database.")
        
        for alma in almas:
            logger.info(f"Indexing Alma: {alma.name} ({alma.alma_type})")
            
            # Create a rich text representation for embedding
            text_to_embed = f"Nome: {alma.name}\nTipo: {alma.alma_type}\nPersonalidade: {alma.personality_descriptor}\nDescrição: {alma.description}"
            
            try:
                vector = await ollama_client.embed(text_to_embed)
                
                payload = {
                    "name": alma.name,
                    "alma_type": alma.alma_type.value if hasattr(alma.alma_type, "value") else str(alma.alma_type),
                    "personality_descriptor": alma.personality_descriptor,
                    "description": alma.description,
                    "system_prompt": alma.system_prompt
                }
                
                await upsert_alma(str(alma.id), vector, payload)
                logger.info(f"Successfully indexed {alma.name}")
            except Exception as e:
                logger.error(f"Failed to index {alma.name}: {e}")

    logger.info("Synchronization complete.")

if __name__ == "__main__":
    asyncio.run(sync_almas_to_qdrant())
