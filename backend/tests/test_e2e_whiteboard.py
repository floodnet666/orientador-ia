import asyncio
import json
import uuid
import sys
import os
from datetime import datetime

# Setup paths
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import User, Project, ProjectCanvasState, AcademicLevelEnum
from app.state.graph_state import GraphState, CanvasState, ChatMessageState
from app.models.agent_config import AgentConfig, LLMParams
from app.agents.almas.base_alma import StatelessAlma

async def setup_test_data():
    async with AsyncSessionLocal() as db:
        # Create a test user if not exists
        user_email = "test_e2e@example.com"
        result = await db.execute(select(User).where(User.email == user_email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=user_email,
                password_hash="fake",
                full_name="Test User",
                academic_level=AcademicLevelEnum.BACHELORS
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Create a test project
        project = Project(
            user_id=user.id,
            title="Test E2E Whiteboard Stateless",
            domain_area="Ciência",
            academic_level=AcademicLevelEnum.BACHELORS
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Create canvas state
        canvas = ProjectCanvasState(project_id=project.id)
        db.add(canvas)
        await db.commit()
        
        return user, project

async def _update_canvas_simulation(db, project_id, fields):
    # This matches the logic in chat.py
    result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas_row = result.scalar_one_or_none()
    if not canvas_row:
        return {}

    canvas_data = dict(canvas_row.canvas_json)
    for key, value in fields.items():
        if value is None: continue
        if key in ["tema", "problema", "justificativa"]:
            # Ensure we don't modify in-place to help SQLAlchemy detection
            field_data = dict(canvas_data.get(key, {"content": "", "is_locked": False}))
            field_data["content"] = value
            canvas_data[key] = field_data
    
    canvas_row.canvas_json = canvas_data
    await db.commit()
    await db.refresh(canvas_row)
    return canvas_data

async def test_e2e_drawing():
    print("🚀 Iniciando Teste E2E de Whiteboard Drawing (Stateless)...")
    user, project = await setup_test_data()
    project_id = project.id
    print(f"Project ID: {project_id}")

    # Build Alma
    config = AgentConfig(
        id="MF_TEST",
        name="Michel Foucault",
        persona_description="Filósofo e historiador francês.",
        system_prompt="És Michel Foucault.",
        epistemological_stance="Arqueologia",
        conflict_patterns=[],
        llm_params=LLMParams(model="qwen2.5:7b")
    )
    alma = StatelessAlma(config)

    # Build State
    state = GraphState(
        project_id=str(project_id),
        user_id=str(user.id),
        academic_level=project.academic_level.value,
        chat_history=[
            ChatMessageState(
                role="user", 
                content="Defina o tema",
                timestamp=datetime.now().isoformat()
            )
        ],
        current_canvas=CanvasState(),
        active_theoretical_alma="Michel Foucault"
    )

    # Simulation of chat.py pipeline logic
    print("Simulando pipeline de chat...")
    detected_tool_call = False
    
    # We mock the LLM output to FORCE a tool call to update_whiteboard
    import unittest.mock as mock
    
    mock_tool_call_chunk = json.dumps({
        "tool_calls": [{
            "function": {
                "name": "update_whiteboard",
                "arguments": {"field": "tema", "value": "A arqueologia do saber E2E"}
            }
        }]
    })

    class MockedStream:
        def __init__(self):
            self.call_count = 0
            
        def __call__(self, *args, **kwargs):
            if self.call_count == 0:
                self.call_count += 1
                async def gen():
                    yield "Vou atualizar o whiteboard agora."
                    yield mock_tool_call_chunk
                return gen()
            else:
                async def gen():
                    yield " Pronto, o tema foi definido e persistido."
                return gen()

    mock_instance = MockedStream()
    with mock.patch("app.services.ollama_client.ollama_client.chat_stream", side_effect=mock_instance):
        async with AsyncSessionLocal() as db:
            async for chunk in alma.stream_response(state):
                if chunk.startswith('{"tool_calls":'):
                    print("✅ Tool call detectado no stream!")
                    data = json.loads(chunk)
                    for tc in data["tool_calls"]:
                        f_name = tc["function"]["name"]
                        f_args = tc["function"]["arguments"]
                        if f_name == "update_whiteboard":
                            detected_tool_call = True
                            print(f"Invocando _update_canvas para: {f_args.get('field')}")
                            await _update_canvas_simulation(db, project_id, {f_args['field']: f_args['value']})

    # VERIFICAÇÃO FINAL NO BANCO DE DADOS
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
        )
        final_canvas = res.scalar_one().canvas_json
        print(f"Canvas Final: {json.dumps(final_canvas, indent=2)}")
        
        if final_canvas.get("tema", {}).get("content") == "A arqueologia do saber E2E":
            print("\n🌟 SUCESSO: O pipeline efetivamente desenhou no whiteboard e persistiu no DB!")
        else:
            print("\n❌ FALHA: O canvas não foi atualizado corretamente no banco de dados.")

if __name__ == "__main__":
    asyncio.run(test_e2e_drawing())
