import asyncio
from qdrant_client import AsyncQdrantClient

async def debug_qdrant():
    client = AsyncQdrantClient(host="qdrant", port=6333)
    print(f"Client type: {type(client)}")
    print(f"Has 'search': {hasattr(client, 'search')}")
    print(f"Has 'query_points': {hasattr(client, 'query_points')}")
    
    # Try a simple search to see if it triggers an error or if it's there
    try:
        print(f"client.search type: {type(client.search)}")
    except Exception as e:
        print(f"Error accessing client.search: {e}")

if __name__ == "__main__":
    asyncio.run(debug_qdrant())
