import asyncio
import logging
from uuid import uuid4
import os

from app.services.empirical.document_processor import empirical_processor
from app.services.qdrant_service import ensure_empirical_collection_v2
from app.api.empirical import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_rag")

async def test_rag():
    try:
        project_id = uuid4()
        pid_str = str(project_id)
        filename = "artigo -a.pdf"
        file_path = "artigo -a.pdf"
        
        logger.info(f"Using Project ID: {pid_str}")
        logger.info(f"Target file path inside docker: {file_path}")
        
        # 1. Ensure collection exists
        await ensure_empirical_collection_v2()
        
        # 2. Process the PDF
        logger.info("Starting process_pdf_v2...")
        try:
            await empirical_processor.process_pdf_v2(file_path, project_id, filename)
            logger.info("PDF processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return
            
        # 3. Test Search
        query = "Qual é o objetivo principal deste artigo?"
        logger.info(f"Testing search with query: '{query}'")
        try:
            results = await empirical_processor.search_evidence(project_id, query, limit=3)
            logger.info(f"Search returned {len(results)} results.")
            for i, res in enumerate(results):
                logger.info(f"Result {i+1} Score: {res.get('score', 0)}")
                logger.debug(f"Result {i+1} Content: {res.get('text', '')[:100]}...")
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag())
