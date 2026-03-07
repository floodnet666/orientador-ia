import asyncio
from qdrant_client import AsyncQdrantClient
from app.config import settings

async def debug_qdrant():
    client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    print(f"Client type: {type(client)}")
    print(f"Has 'search': {hasattr(client, 'search')}")
    print(f"All attributes: {[attr for attr in dir(client) if not attr.startswith('_')]}")

if __name__ == "__main__":
    asyncio.run(debug_qdrant())
