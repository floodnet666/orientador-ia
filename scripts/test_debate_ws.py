import asyncio
import json
import logging
import os
import sys
from uuid import UUID
from datetime import datetime
import websockets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

# Add backend to path to import config/models
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.config import settings
from app.models.sql_models import User, Project

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test.debate_ws")

async def get_test_credentials():
    """Busca o primeiro usuário e projeto disponível para o teste."""
    DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Nenhum usuário encontrado no DB.")
            
        project_result = await db.execute(select(Project).where(Project.user_id == user.id).limit(1))
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Nenhum projeto encontrado para o usuário {user.email}.")
            
        return user, project

def create_token(user_id: str):
    """Gera um token JWT válido para o WebSocket."""
    to_encode = {"sub": str(user_id)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

async def run_debate_test():
    try:
        user, project = await get_test_credentials()
        token = create_token(user.id)
        
        uri = f"ws://localhost:8000/api/chat/{project.id}/ws?token={token}"
        log.info(f"Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            # Espera carregar/conexão
            msg = await websocket.recv()
            log.info(f"Received: {msg}")
            
            # Envia gatilho de debate
            debate_trigger = {
                "type": "message",
                "content": "Vamos fazer um debate sobre o tema do projeto."
            }
            log.info(f"Sending trigger: {debate_trigger['content']}")
            await websocket.send(json.dumps(debate_trigger))
            
            # Monitora eventos
            async for message in websocket:
                data = json.loads(message)
                log.info(f"Event: {data.get('type')} | Content: {str(data.get('content', data.get('message', ''))[:100])}")
                
                if data.get("type") == "error":
                    log.error(f"FAIL: Received error event: {data.get('message')}")
                    return False
                
                if data.get("type") == "panel_selected":
                    log.info("SUCCESS: Panel selected successfully!")
                    # Podemos parar aqui se o objetivo for apenas testar o seletor de painel
                    return True
                    
                if data.get("type") == "done":
                    log.info("Debate finished successfully.")
                    return True
                    
    except Exception as e:
        log.error(f"Test crashed: {e}")
        return False

if __name__ == "__main__":
    if asyncio.run(run_debate_test()):
        log.info("TEST PASSED")
        sys.exit(0)
    else:
        log.info("TEST FAILED")
        sys.exit(1)
