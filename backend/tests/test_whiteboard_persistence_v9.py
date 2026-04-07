import pytest
import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import Project, ProjectCanvasState, User
from app.api.chat import _update_canvas

@pytest.mark.asyncio
async def test_whiteboard_node_persistence():
    """
    Testa se o banco de dados é atualizado corretamente com um nó de canvas.
    Este teste simula a ação que deve ser disparada pelo interceptador on_tool_end.
    """
    async with AsyncSessionLocal() as db:
        # 1. Setup - Garantir um projeto real para teste (ou falhar se não houver)
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        if not user:
            pytest.skip("No user found in DB")
            
        project = Project(
            user_id=user.id,
            title="TDD Whiteboard Test",
            domain_area="Physics",
            academic_level="GRADUATION"
        )
        db.add(project)
        await db.flush()
        
        canvas_state = ProjectCanvasState(project_id=project.id)
        db.add(canvas_state)
        await db.commit()
        
        project_id = project.id
        
        # 2. Action - Simular a inserção de um nó via tool call arguments
        node_payload = {
            "id": "node_tdd_1",
            "label": "Test Node Persistence",
            "type": "MF"
        }
        
        print(f"Applying _update_canvas for project {project_id}")
        await _update_canvas(db, project_id, {"canvas_node": node_payload})
        
        # 3. Verification - O banco deve conter o nó no campo mapa_mental.nodes
        await db.refresh(canvas_state)
        mm = canvas_state.canvas_json.get("mapa_mental", {})
        nodes = mm.get("nodes", [])
        
        found = any(n.get("id") == "node_tdd_1" for n in nodes)
        
        # Cleanup
        await db.execute(select(Project).filter(Project.id == project_id))
        await db.delete(canvas_state)
        await db.delete(project)
        await db.commit()
        
        assert found, "Nó não foi encontrado no ProjectCanvasState após _update_canvas"
        print("✅ SUCCESS: Node persistence verified.")

if __name__ == "__main__":
    asyncio.run(test_whiteboard_node_persistence())
