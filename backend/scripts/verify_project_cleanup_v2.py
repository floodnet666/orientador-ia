import asyncio
import os
import sys
from uuid import uuid4

# Add the backend app to the path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.sql_models import Project, ChatMessage, ProjectCanvasState, User
from app.services.qdrant_service import get_qdrant, delete_project_data
import redis.asyncio as redis
from app.config import settings

async def verify_cleanup():
    print("🚀 Starting Extended Project Cleanup Verification...")
    
    async with AsyncSessionLocal() as db:
        # 1. Get a user
        result = await db.execute(select(User).limit(1))
        user = result.scalars().first()
        if not user:
            print("❌ No user found in DB. Please run seed_almas.py first.")
            return

        # 2. Create a dummy project
        project_id = uuid4()
        project = Project(
            id=project_id,
            title=f"Test Cleanup {project_id.hex[:6]}",
            user_id=user.id,
            domain_area="Testing",
            academic_level=user.academic_level
        )
        db.add(project)
        await db.flush()
        
        # 3. Add associated data in Postgres
        msg = ChatMessage(project_id=project_id, role="user", content="Hello cleanup")
        canvas = ProjectCanvasState(project_id=project_id, canvas_json={"test": True})
        db.add(msg)
        db.add(canvas)
        await db.commit()
        print(f"✅ Created dummy project {project_id} with msg and canvas state.")

        # 4. Add dummy data in Qdrant
        q_client = get_qdrant()
        from qdrant_client.http import models
        
        # Ensure collection exists (it should, but just in case for testing)
        try:
            await q_client.upsert(
                collection_name="empirical_data_v2",
                points=[
                    models.PointStruct(
                        id=str(uuid4()),
                        vector=[0.1] * 1024, # Assume 1024 for mxbai or similar
                        payload={"project_id": str(project_id), "text": "Dummy evidence"}
                    )
                ]
            )
            print("✅ Added dummy chunk to Qdrant.")
        except Exception as e:
            print(f"⚠️ Failed to add Qdrant chunk (is it running?): {e}")

        # 5. Add dummy key in Redis
        r_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_key = f"ingest:{str(project_id)}:test_doc"
        await r_client.set(redis_key, "processing")
        print(f"✅ Added dummy Redis key: {redis_key}")

        # --- SIMULATE DELETION ---
        print("\n🧹 Simulating deletion via service calls...")
        
        # A. Qdrant Cleanup
        await delete_project_data(str(project_id))
        print("Done Qdrant cleanup.")
        
        # B. Redis Cleanup
        keys = await r_client.keys(f"ingest:{str(project_id)}:*")
        if keys:
            await r_client.delete(*keys)
        print("Done Redis cleanup.")
        
        # C. DB Delete (Cascades)
        await db.delete(project)
        await db.commit()
        print("Done DB deletion.")

        # --- VERIFICATION ---
        print("\n🔍 Verifying cleanup...")
        
        # Postgres check
        msg_exists = (await db.execute(select(ChatMessage).where(ChatMessage.project_id == project_id))).scalars().first()
        canvas_exists = (await db.execute(select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id))).scalars().first()
        proj_exists = await db.get(Project, project_id)
        
        if not proj_exists and not msg_exists and not canvas_exists:
            print("✅ Postgres: Project and all associated data deleted successfully.")
        else:
            print(f"❌ Postgres: Data leakage! Project: {proj_exists}, Msg: {msg_exists}, Canvas: {canvas_exists}")

        # Qdrant check
        search_result = await q_client.scroll(
            collection_name="empirical_data_v2",
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=str(project_id)))]
            )
        )
        if not search_result[0]:
            print("✅ Qdrant: Project vectors cleaned successfully.")
        else:
            print(f"❌ Qdrant: Found leftover vectors: {len(search_result[0])} points.")

        # Redis check
        redis_leftovers = await r_client.keys(f"ingest:{str(project_id)}:*")
        if not redis_leftovers:
            print("✅ Redis: All ingestion status keys cleared.")
        else:
            print(f"❌ Redis: Found leftover keys: {redis_leftovers}")

    print("\n🏁 Cleanup Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_cleanup())
