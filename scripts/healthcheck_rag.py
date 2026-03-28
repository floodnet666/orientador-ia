import sys
import asyncio
import logging
import json
import urllib.request
from pathlib import Path

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("healthcheck")

async def verify_ollama():
    """Verify Ollama is reachable and can run authorized models."""
    try:
        # Check tags (increase to 30s)
        logger.info("Verifying Ollama tags...")
        response = urllib.request.urlopen("http://host.docker.internal:11434/api/tags", timeout=30)
        data = json.loads(response.read().decode())
        models = [m['name'] for m in data.get('models', [])]
        logger.info(f"Ollama reachable. Models found: {len(models)}")
        
        # 1. Test Chat (MANDATORY MODEL: qwen2.5:7b)
        logger.info("Verifying Ollama Chat (qwen2.5:7b)... This may take time if model is loading.")
        payload_chat = json.dumps({
            "model": "qwen2.5:7b",
            "messages": [{"role": "user", "content": "olá"}],
            "stream": False
        }).encode()
        req_chat = urllib.request.Request("http://host.docker.internal:11434/api/chat", data=payload_chat)
        with urllib.request.urlopen(req_chat, timeout=180) as res:
            logger.info("Ollama Chat (qwen2.5:7b): SUCCESS")

        # 2. Test embedding
        logger.info("Verifying Ollama Embedding (nomic-embed-text-v2-moe:latest)...")
        payload_embed = json.dumps({
            "model": "nomic-embed-text-v2-moe:latest",
            "prompt": "Healthcheck verification query"
        }).encode()
        req_embed = urllib.request.Request("http://host.docker.internal:11434/api/embeddings", data=payload_embed)
        with urllib.request.urlopen(req_embed, timeout=60) as res:
            logger.info("Ollama Embedding: SUCCESS")
            
        return True
    except Exception as e:
        logger.error(f"Ollama Healthcheck FAILED: {e}")
        return False

async def verify_qdrant():
    """Verify Qdrant is reachable."""
    try:
        response = urllib.request.urlopen("http://qdrant:6333/healthz", timeout=10)
        if response.status == 200:
            logger.info("Qdrant reachable: SUCCESS")
            return True
        return False
    except Exception as e:
        logger.error(f"Qdrant Healthcheck FAILED: {e}")
        return False

async def main():
    logger.info("Starting Orientador.IA RAG Healthcheck (v2 - High Timeout)...")
    
    ollama_ok = await verify_ollama()
    qdrant_ok = await verify_qdrant()
    
    if ollama_ok and qdrant_ok:
        logger.info("=== RAG SYSTEM VERIFIED: ALL SYSTEMS OPERATIONAL ===")
        sys.exit(0)
    else:
        logger.critical("!!! RAG SYSTEM FAILURE: Startup verification FAILED !!!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
