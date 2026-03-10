import asyncio
from uuid import UUID
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import EcosystemResource

async def test_update():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(EcosystemResource))
        alma = result.scalars().first()
        if not alma:
            print("No Alma found")
            return
        
        print(f"Current model: {alma.llm_model}")
        alma_id = alma.id
        
        # Simulating what the API does
        alma.llm_model = "test-model-persistence"
        await db.commit()
        
        # Verify
        await db.refresh(alma)
        print(f"Updated model: {alma.llm_model}")
        
        if alma.llm_model == "test-model-persistence":
            print("SUCCESS: Persistence working in DB")
        else:
            print("FAILED: Persistence NOT working")

if __name__ == "__main__":
    asyncio.run(test_update())
