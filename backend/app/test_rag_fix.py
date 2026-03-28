import asyncio
import uuid
from app.api.chat import _build_graph_state
from app.agents.orchestrator import orchestrate
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.sql_models import User, Project
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_rag")

async def test_maestro_sees_docs():
    project_id = uuid.UUID("45d08640-5f18-4a32-a46c-eff4660fb776")
    user_email = "sphoka@gmail.com"
    
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one_or_none()
        if not user:
            logger.error("User not found")
            return

        logger.info("Building GraphState for project %s", project_id)
        state = await _build_graph_state(project_id, user, db)
        
        logger.info("Documents found in state: %s", [doc.filename for doc in state.empirical_documents])
        
        if not state.empirical_documents:
            logger.warning("No documents found! This is the bug we are fixing.")
        else:
            logger.info("SUCCESS: GraphState has %d documents.", len(state.empirical_documents))

        logger.info("Testing Orchestrator decision...")
        decision = await orchestrate(state, "O que dizem os documentos que eu enviei?")
        logger.info("Orchestrator decision: %s", decision)
        
        if "empirical_documents" in decision.get("directive", "").lower() or len(state.empirical_documents) > 0:
            logger.info("FINAL VERIFICATION: Maestro is aware of the context.")
        else:
            logger.error("Maestro still unaware of documents.")

if __name__ == "__main__":
    asyncio.run(test_maestro_sees_docs())
