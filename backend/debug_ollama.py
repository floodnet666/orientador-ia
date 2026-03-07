import asyncio
import httpx
import json

async def check_ollama():
    base_url = "http://localhost:11434" # Assuming local access for diagnosis if running from host
    print(f"Checking Ollama at {base_url}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Check Tags
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"Available models: {models}")
            else:
                print(f"Failed to get tags: {resp.status_code}")
                
            # 2. Test Chat
            payload = {
                "model": "qwen3.5:4b",
                "messages": [{"role": "user", "content": "olá"}],
                "stream": False
            }
            print(f"Testing chat with qwen3.5:4b...")
            resp = await client.post(f"{base_url}/api/chat", json=payload)
            if resp.status_code == 200:
                print(f"Chat response: {resp.json()['message']['content']}")
            else:
                print(f"Chat failed: {resp.status_code} - {resp.text}")
                
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())
