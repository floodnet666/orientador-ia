import asyncio
import logging
from uuid import UUID

from app.services.empirical.document_processor import empirical_processor
from app.agents.almas.base_alma import BaseAlma
from app.state.graph_state import GraphState, CanvasState, ChatMessageState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_query")

async def test_find_and_query():
    # 1. Find the project ID in Qdrant
    try:
        from qdrant_client import models
        collection_name = "empirical_data_v2"
        results = await empirical_processor.qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename", match=models.MatchValue(value="artigo -a.pdf")
                    )
                ]
            ),
            limit=1,
            with_payload=True
        )
        
        points = results[0]
        if not points:
            logger.error("No chunks found for 'artigo -a.pdf'")
            return
            
        project_id = points[0].payload.get("project_id")
        logger.info(f"Using Project ID found: {project_id}")
            
        # 2. Query the Alma agent
        logger.info("Testing Alma response...")
        alma = BaseAlma("Foucault", "Responda apenas com base nos documentos.", "Metódico.")
        
        state = GraphState(
            project_id=project_id,
            user_id="test",
            academic_level="mestrado",
            chat_history=[
                ChatMessageState(role="user", content='Qual é o objetivo principal deste artigo que acabei de enviar ("artigo -a.pdf")?', timestamp="2024-01-01T00:00:00Z")
            ],
            current_canvas=CanvasState()
        )
        
        response = ""
        async for chunk in alma.stream_response(state):
            response += chunk
            
        logger.info(f"Alma Response:\n{response}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_find_and_query())
