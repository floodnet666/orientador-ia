import asyncio
import httpx

async def check_ollama_models():
    base_url = "http://host.docker.internal:11434"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"Models: {models}")
                if "nomic-embed-text-v2-moe:latest" in models or "nomic-embed-text-v2-moe" in models:
                    print("SUCCESS: nomic-embed-text-v2-moe is available")
                else:
                    print("WARNING: nomic-embed-text-v2-moe is MISSING")
            else:
                print(f"Error: {resp.status_code}")
        except Exception as e:
            print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama_models())
