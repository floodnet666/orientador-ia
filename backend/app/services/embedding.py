from app.services.ollama_client import ollama_client


async def generate_embedding(text: str) -> list[float]:
    return await ollama_client.embed(text)
