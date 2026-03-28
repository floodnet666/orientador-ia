import asyncio
import logging
from uuid import uuid4

from app.services.empirical.document_processor import empirical_processor
from app.services.qdrant_service import ensure_empirical_collection_v2
from app.agents.almas.base_alma import BaseAlma
from app.state.graph_state import GraphState, CanvasState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_alma_rag")

async def test_alma_rag():
    try:
        project_id = uuid4()
        pid_str = str(project_id)
        filename = "artigo -a.pdf"
        file_path = "artigo -a.pdf"
        
        logger.info(f"Using Project ID: {pid_str}")
        
        await ensure_empirical_collection_v2()
        logger.info("Starting process_pdf_v2...")
        try:
            await empirical_processor.process_pdf_v2(file_path, project_id, filename)
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return
            
        logger.info("Testing Alma response...")
        # Create a dummy Alma
        alma = BaseAlma("Tester", "Responda apenas com base nos documentos do projeto se necessário.", "Você é um ajudante.")
        
        # Create a dummy GraphState
        state = GraphState(
            project_id=pid_str,
            user_id=str(uuid4()),
            chat_history=[
                {"role": "user", "content": "Qual é o objetivo principal deste artigo que acabei de enviar?"}
            ],
            current_canvas=CanvasState()
        )
        
        # Stream response
        response = ""
        async for chunk in alma.stream_response(state):
            response += chunk
            
        logger.info(f"Alma Response:\n{response}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_alma_rag())
