import pytest
from httpx import AsyncClient
from app.models.sql_models import User, AcademicLevelEnum, EcosystemResource, ResourceTypeEnum
from app.api.auth import hash_password, create_token

@pytest.fixture
async def admin_user(db_session):
    user = User(
        email="admin@test.com",
        password_hash=hash_password("adminpass"),
        full_name="Admin Test",
        academic_level=AcademicLevelEnum.PHD,
        is_admin=True
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
def admin_token(admin_user):
    return create_token(str(admin_user.id))

@pytest.fixture
async def normal_user(db_session):
    user = User(
        email="normal@test.com",
        password_hash=hash_password("normalpass"),
        full_name="Normal Test",
        academic_level=AcademicLevelEnum.MASTERS,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
def normal_token(normal_user):
    return create_token(str(normal_user.id))

@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_token, normal_token):
    # Admin can access
    res = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

    # Normal user cannot
    res2 = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {normal_token}"})
    assert res2.status_code == 403

@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, admin_token, db_session):
    payload = {
        "email": "newuser@test.com",
        "full_name": "New User",
        "password": "pwd",
        "academic_level": "HIGHSCHOOL"
    }
    res = await client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "newuser@test.com"

@pytest.mark.asyncio
async def test_admin_almas_crud(client: AsyncClient, admin_token, db_session):
    # Create Alma
    payload = {
        "name": "Test Alma",
        "description": "Desc",
        "resource_type": "ALMA",
        "alma_type": "THEORETICAL",
        "system_prompt": "You are a test.",
        "personality_descriptor": "Testing",
        "llm_model": "gpt-4",
    }
    res = await client.post("/api/admin/almas", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    alma = res.json()
    alma_id = alma["id"]

    # Read Almas
    res2 = await client.get("/api/admin/almas", headers={"Authorization": f"Bearer {admin_token}"})
    assert res2.status_code == 200
    assert any(a["id"] == alma_id for a in res2.json())

    # Update Prompt (History test)
    res3 = await client.post(f"/api/admin/almas/{alma_id}/prompt", json={"new_prompt": "New prompt here", "reason": "Test reason"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res3.status_code == 200

    # Get History
    res4 = await client.get(f"/api/admin/almas/{alma_id}/history", headers={"Authorization": f"Bearer {admin_token}"})
    assert res4.status_code == 200
    history = res4.json()
    assert len(history) == 1
    assert history[0]["previous_prompt"] == "You are a test."
    history_id = history[0]["id"]

    # Rollback
    res5 = await client.post(f"/api/admin/almas/{alma_id}/rollback/{history_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res5.status_code == 200

    # Check History again to see the rollback added a new record
    res6 = await client.get(f"/api/admin/almas/{alma_id}/history", headers={"Authorization": f"Bearer {admin_token}"})
    assert res6.status_code == 200
    assert len(res6.json()) == 2

@pytest.mark.asyncio
async def test_admin_metrics(client: AsyncClient, admin_token):
    res = await client.get("/api/admin/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "recent_metrics" in data
    assert "average_duration_ms" in data

@pytest.mark.asyncio
async def test_observability_slow_llm(client: AsyncClient, admin_token, db_session):
    import asyncio
    from app.models.sql_models import SystemMetric
    from sqlalchemy import select

    # We mock a slow request to simulate an LLM call taking > 40s by directly inserting a metric,
    # or invoking a route that uses the observability middleware and we mock asyncio.sleep.
    # A cleaner test for the metrics storage: 
    # Just insert a > 40s metric and verify the admin endpoint retrieves it properly.
    slow_metric = SystemMetric(
        endpoint="/api/chat/stream",
        duration_ms=45000,
        status_code=200,
        error_message=None
    )
    db_session.add(slow_metric)
    await db_session.commit()

    res = await client.get("/api/admin/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    data = res.json()
    assert res.status_code == 200
    assert data["slow_queries_count"] >= 1
    assert any(m["duration_ms"] == 45000 for m in data["recent_metrics"])
