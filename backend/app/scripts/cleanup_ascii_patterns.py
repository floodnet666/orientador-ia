import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import AsyncSessionLocal
from app.models.sql_models import ChatMessage
from sqlalchemy import select, delete, or_

async def cleanup():
    print("🚀 Iniciando expurgo de alucinações ASCII do Whiteboard...")
    async with AsyncSessionLocal() as session:
        # Padrões de alucinação comuns detectados
        patterns = [
            "%### Whiteboard Update%",
            "%### Whiteboard Layout%",
            "%+---+%",
            "%|   |%",
            "%|---|%"
        ]
        
        conditions = [ChatMessage.content.like(p) for p in patterns]
        
        # Primeiro, vamos contar
        stmt = select(ChatMessage).where(or_(*conditions))
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        count = len(messages)
        if count == 0:
            print("✅ Nenhuma alucinação encontrada. O banco está limpo.")
            return

        print(f"⚠️ Encontradas {count} mensagens contaminadas. Deletando...")
        
        delete_stmt = delete(ChatMessage).where(or_(*conditions))
        await session.execute(delete_stmt)
        await session.commit()
        
        print(f"✨ Expurgo concluído. {count} mensagens removidas.")

if __name__ == "__main__":
    asyncio.run(cleanup())
