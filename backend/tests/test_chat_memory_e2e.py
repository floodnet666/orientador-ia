
import pytest
import uuid
from httpx import AsyncClient
from app.main import app
from app.api.auth import create_token
from app.models.sql_models import User, AcademicLevelEnum
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.mark.asyncio
async def test_chat_memory_pipeline_e2e(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup User and Auth with correct schema
    email = f"test_e2e_{uuid.uuid4().hex[:6]}@example.com"
    user = User(
        email=email,
        full_name="E2E Tester",
        password_hash=pwd_context.hash("1234"),
        academic_level=AcademicLevelEnum.PHD
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    token = create_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Project
    project_payload = {
        "title": "E2E Test Project",
        "domain_area": "Sociologia",
        "academic_level": "PHD"
    }
    resp = await client.post("/api/projects/", json=project_payload, headers=headers)
    assert resp.status_code in (200, 201), f"Project creation failed: {resp.text}"
    project_data = resp.json()
    project_id = project_data["id"]
    
    # 3. Test Chat History (Short Term Memory)
    chat_resp = await client.get(f"/api/chat/{project_id}/history", headers=headers)
    assert chat_resp.status_code == 200
    assert isinstance(chat_resp.json(), list)
    
    # 4. External Search Tool Logic Test

    print("🏁 E2E Validation Phase 1 Complete")
