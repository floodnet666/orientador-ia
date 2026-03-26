import asyncio
import httpx
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
USER_INPUT = "Gostava de focar a minha tese em arquiteturas reativas e usar OpenMAIC. Desenha o esqueleto e os componentes principais disso no whiteboard."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_whiteboard",
            "description": "Atualiza o whiteboard visual do utilizador com novos dados textuais. Use sempre que o utilizador pedir para 'desenhar' ou 'escrever' no quadro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "A secção do whiteboard a atualizar. Ex: 'tema', 'problema', 'arquitetura', 'objetivos'",
                    },
                    "value": {
                        "type": "string",
                        "description": "O conteúdo detalhado a escrever nesta secção do whiteboard.",
                    }
                },
                "required": ["field", "value"],
            },
        },
    }
]


async def run_tool_test(model_name: str):
    print(f"\n{'='*70}")
    print(f"MODELO: {model_name} | MODO: OLLAMA NATIVE TOOL CALLING")
    print(f"{'='*70}")
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "És o Orientador.IA. Usa as ferramentas disponíveis para interagir com o ambiente (Whiteboard)."},
            {"role": "user", "content": USER_INPUT}
        ],
        "tools": TOOLS,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            message = data.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            print("\n>>> TEXTO LIVRE RETORNADO:")
            print(content if content else "(sem texto)")
            
            print("\n>>> FERRAMENTAS INVOCADAS (NATIVE):")
            if not tool_calls:
                print("❌ NENHUMA FERRAMENTA INVOCADA - O modelo falhou em usar Tool Calling nativo.")
            else:
                for idx, tc in enumerate(tool_calls):
                    print(f"✅ {idx+1}. FUNÇÃO: {tc.get('function', {}).get('name')}")
                    print(f"       ARGS: {json.dumps(tc.get('function', {}).get('arguments'))}")
                    
            print("\n" + "-"*70 + "\n")
            
    except Exception as e:
        print(f"ERRO com {model_name}: {e}\n")


async def main():
    modelos = [
        "qwen2.5:7b"
    ]
    
    for modelo in modelos:
        print(f"\n>>>> INICIANDO TESTE COM FERRAMENTAS (NATIVE) PARA: {modelo} <<<<\n", flush=True)
        await run_tool_test(modelo)

if __name__ == "__main__":
    asyncio.run(main())
