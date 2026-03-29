import pytest
import asyncio
import uuid
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.agents.graph_factory import create_backend_graph
from app.agents.state import BackendState

@pytest.mark.async_io
async def test_graph_basic_flow():
    """Valida o fluxo básico Maestro -> Alma no LangGraph."""
    graph = create_backend_graph()
    
    # Estado inicial simulado
    initial_state = BackendState(
        messages=[HumanMessage(content="Olá, quem é você?")],
        project_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        selected_soul_id=None,
        canvas_state={},
        metadata={"thread_id": "test_thread"}
    )
    
    # Execução do grafo
    config = {"configurable": {"thread_id": "test_thread"}}
    
    collected_messages = list(initial_state["messages"])
    print(f"\nInitial message count: {len(collected_messages)}")

    async for event in graph.astream(initial_state, config=config):
        for node, values in event.items():
            print(f"\n--- Node: {node} ---")
            if "messages" in values:
                new_msgs = values["messages"]
                print(f"Node produced {len(new_msgs)} new messages")
                collected_messages.extend(new_msgs)
                for m in new_msgs:
                    print(f"  Content snippet: {m.content[:100]}...")

    print(f"\nFinal message count: {len(collected_messages)}")
    assert len(collected_messages) > 1
    # Verifica se há alguma mensagem do assistente (AI)
    assert any(isinstance(m, AIMessage) for m in collected_messages)
    print("Test passed logic verification!")

if __name__ == "__main__":
    # Permite rodar via python se pytest não estiver configurado
    async def run_test():
        try:
            await test_graph_basic_flow()
            print("\nTest passed!")
        except Exception as e:
            print(f"\nTest failed: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(run_test())
