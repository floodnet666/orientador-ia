from uuid import UUID
import asyncio
import json
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import ProjectCanvasState

async def migrate_canvas_data():
    print("🚀 Starting Canvas data migration...")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProjectCanvasState))
        canvas_rows = res.scalars().all()
        
        migrated_count = 0
        for row in canvas_rows:
            data = dict(row.canvas_json) if row.canvas_json else {}
            changed = False
            
            for key in ["tema", "problema", "justificativa"]:
                if key in data and isinstance(data[key], str):
                    print(f"📦 Migrating field '{key}' for project {row.project_id}")
                    data[key] = {"content": data[key], "is_locked": False}
                    changed = True
            
            if changed:
                row.canvas_json = data
                migrated_count += 1
        
        if migrated_count > 0:
            await db.commit()
            print(f"✅ Successfully migrated {migrated_count} canvas rows.")
        else:
            print("ℹ️ No rows needed migration.")

if __name__ == "__main__":
    asyncio.run(migrate_canvas_data())
