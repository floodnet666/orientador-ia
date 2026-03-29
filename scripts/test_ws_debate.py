import asyncio
import websockets
import json
import sys

async def test_debate():
    uri = "ws://localhost:8000/api/v1/chat/ws/debug-project?token=DEBUG"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # Envia comando de debate
            payload = {"content": "/debate O impacto da IA na educação"}
            await websocket.send(json.dumps(payload))
            print("SENT: /debate command")

            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    msg_type = data.get("type")
                    print(f"RECV: {msg_type}")

                    # Se receber o manifesto ou o painel, o backend está processando o debate
                    if msg_type in ["debate_manifest", "panel_selected"]:
                        print("SUCCESS: Debate Mode initialized and broadcasting.")
                    
                    # Se receber chunk, o debate está em curso
                    if msg_type == "debate_chunk":
                        # Só printa o primeiro pra não poluir
                        print("SUCCESS: Receiving debate chunks...")

                    if msg_type in ["debate_done", "error"]:
                        print(f"TERMINATED: {msg_type}")
                        break
                except asyncio.TimeoutError:
                    print("TIMEOUT: No message received for 30s")
                    break
    except Exception as e:
        print(f"FAILED: Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Garante que websockets está instalado
    try:
        import websockets
    except ImportError:
        import subprocess
        print("Installing websockets...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        import websockets
    
    asyncio.run(test_debate())
