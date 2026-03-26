import asyncio
import httpx
import json
import logging

# Configurar logs para ver o que o cliente faz
logging.basicConfig(level=logging.INFO)

async def test_full_pipeline_tool_calling():
    # Simulando o que o BaseAlma faria agora
    messages = [
        {"role": "system", "content": "És o Orientador.IA. Usa a ferramenta update_whiteboard para registar o progresso."},
        {"role": "user", "content": "Define o tema da minha tese sobre Cidades Inteligentes e Reatividade."}
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "update_whiteboard",
                "description": "Materializa progresso no canvas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": ["tema", "problema"]},
                        "value": {"type": "string"}
                    },
                    "required": ["field", "value"]
                }
            }
        }
    ]

    print("\n>>> TESTANDO QWEN2.5:7B COM TOOLS REAIS <<<")
    payload = {
        "model": "qwen2.5:7b",
        "messages": messages,
        "tools": tools,
        "stream": True # Testar a stream pois é o que o chat.py usa
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line: continue
                data = json.loads(line)
                msg = data.get("message", {})
                
                if "tool_calls" in msg:
                    print(f"\n✅ SUCESSO! TOOL CALL DETECTADO NA STREAM: {json.dumps(msg['tool_calls'])}")
                
                content = msg.get("content", "")
                if content:
                    print(content, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(test_full_pipeline_tool_calling())
