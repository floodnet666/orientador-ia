import asyncio
import sys
import json
from app.services.ollama_client import ollama_client
from app.core.config import settings

async def main():
    print("Testing live Ollama Stream...")
    model = "qwen2.5:7b"  # User target
    print(f"Targeting model: {model}")
    
    prompt = "Escreva 1 frase curta sobre física com uma fórmula $E=mc^2$ e retorne [ACTION:{\"type\":\"CANVAS_NODE\",\"payload\":{\"id\":\"n1\",\"label\":\"Einstein\"}}]"
    context = [{"role": "user", "content": prompt}]
    
    print("\n--- STREAM START ---")
    try:
        async for chunk in ollama_client.chat_stream(
            model=model,
            messages=context,
            system="Responda em português.",
            tools=None
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n--- STREAM END ---")
        print("\n✅ Ollama respondeu e o stream funcionou corretamente.")
    except Exception as e:
        print(f"\n❌ Erro no stream: {e}")

if __name__ == "__main__":
    asyncio.run(main())
