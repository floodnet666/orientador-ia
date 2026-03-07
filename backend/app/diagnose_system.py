from uuid import UUID
import asyncio
import json
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import Project, ProjectCanvasState, ChatMessage, User
from app.api.chat import _build_graph_state
from app.agents.orchestrator import orchestrate
from app.agents.canvas_extractor import extract_canvas_fields

logging.basicConfig(level=logging.INFO)

async def run_diagnostics(project_id_str: str):
    pid = UUID(project_id_str)
    print(f"\n=== Diagnostics for Project: {pid} ===")
    
    async with AsyncSessionLocal() as db:
        # 1. Check Project and User
        res = await db.execute(select(Project).where(Project.id == pid))
        project = res.scalar_one_or_none()
        if not project:
            print("❌ Project not found in DB")
            return
        print(f"✅ Project Found: {project.title} (Level: {project.academic_level})")
        
        user_res = await db.execute(select(User).where(User.id == project.user_id))
        user = user_res.scalar_one_or_none()
        print(f"✅ User Found: {user.email if user else 'N/A'}")

        # 2. Check Canvas State
        res_c = await db.execute(select(ProjectCanvasState).where(ProjectCanvasState.project_id == pid))
        canvas = res_c.scalar_one_or_none()
        canvas_data = canvas.canvas_json if canvas else {}
        print(f"🔍 Canvas JSON: {json.dumps(canvas_data, indent=2)}")

        # 3. Check Chat History
        res_m = await db.execute(select(ChatMessage).where(ChatMessage.project_id == pid).order_by(ChatMessage.created_at.desc()).limit(3))
        msgs = res_m.scalars().all()
        print("📜 Last 3 Messages:")
        for m in msgs:
            print(f"  - [{m.role}] {m.content[:100]}...")

        # 4. Test Graph State Construction
        try:
            from app.state.graph_state import CanvasState, GraphState
            # Handle potential empty string or nulls in DB
            if not canvas_data:
                canvas_obj = CanvasState()
            else:
                # Filter out keys that don't belong to CanvasState if any
                allowed_keys = CanvasState.model_fields.keys()
                filtered_data = {k: v for k, v in canvas_data.items() if k in allowed_keys}
                # Fix nested types if they are strings instead of dicts
                for key in ["tema", "problema", "justificativa"]:
                    if key in filtered_data and isinstance(filtered_data[key], str):
                        filtered_data[key] = {"content": filtered_data[key], "is_locked": False}
                
                canvas_obj = CanvasState(**filtered_data)

            state = await _build_graph_state(pid, user, db)
            print("✅ GraphState built successfully")
        except Exception as e:
            print(f"❌ Failed to build GraphState: {e}")
            import traceback
            traceback.print_exc()
            return

        # 5. Test Orchestrator
        print("\n--- Testing Orchestrator (using 0.8b for speed) ---")
        test_msg = "Explique o conceito de biopoder"
        try:
            # Temporarily override settings for test
            from app.config import settings
            old_model = settings.OLLAMA_ORCHESTRATOR_MODEL
            settings.OLLAMA_ORCHESTRATOR_MODEL = "qwen3.5:0.8b"
            
            decision = await orchestrate(state, test_msg)
            print(f"🤖 Orchestrator Decision: {json.dumps(decision, indent=2)}")
            
            settings.OLLAMA_ORCHESTRATOR_MODEL = old_model
        except Exception as e:
            print(f"❌ Orchestrator Failed: {e}")

        # 6. Test Canvas Extraction
        print("\n--- Testing Canvas Extraction ---")
        try:
            extracted = await extract_canvas_fields(state)
            print(f"🖼️ Extracted Fields: {json.dumps(extracted, indent=2)}")
        except Exception as e:
            print(f"❌ Canvas Extraction Failed: {e}")

if __name__ == "__main__":
    import sys
    project_id = sys.argv[1] if len(sys.argv) > 1 else "b30a2ab1-6e7f-4bf5-8cc2-26cae3e5e21d"
    asyncio.run(run_diagnostics(project_id))
