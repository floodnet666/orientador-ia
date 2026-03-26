import asyncio
import sys
import os

# Setup paths
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import AsyncSessionLocal
from app.models.sql_models import EcosystemResource
from sqlalchemy import select

async def check_db():
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(EcosystemResource))
            almas = result.scalars().all()
            print(f"Total Almas: {len(almas)}")
            for a in almas:
                print(f"- {a.name} ({a.resource_type})")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
