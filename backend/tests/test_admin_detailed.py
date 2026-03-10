import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from app.models.sql_models import User, AcademicLevelEnum, EcosystemResource, ResourceTypeEnum, AlmaPromptHistory, SystemMetric
from app.api.auth import hash_password, create_token

@pytest.fixture
async def admin_user(db_session):
    user = User(
        email="admin_detailed@test.com",
        password_hash=hash_password("adminpass"),
        full_name="Admin Detailed Test",
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
        email="normal_detailed@test.com",
        password_hash=hash_password("normalpass"),
        full_name="Normal Detailed Test",
        academic_level=AcademicLevelEnum.MASTERS,
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
def normal_token(normal_user):
    return create_token(str(normal_user.id))

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient, normal_token):
    """Test that non-admin users cannot access admin endpoints."""
    endpoints = [
        ("GET", "/api/admin/users"),
        ("POST", "/api/admin/users"),
        ("GET", "/api/admin/almas"),
        ("POST", "/api/admin/almas"),
        ("GET", "/api/admin/metrics"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = await client.get(path, headers={"Authorization": f"Bearer {normal_token}"})
        else:
            res = await client.post(path, json={}, headers={"Authorization": f"Bearer {normal_token}"})
        assert res.status_code == 403, f"Endpoint {path} should be restricted"

@pytest.mark.asyncio
async def test_user_management_extended(client: AsyncClient, admin_token, db_session):
    """Test full User CRUD and password reset edge cases."""
    # Create
    payload = {
        "email": "crud_user@test.com",
        "full_name": "CRUD User",
        "password": "initial_password",
        "academic_level": "PHD"
    }
    res = await client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    user_id = res.json()["id"]

    # Reset Password
    reset_payload = {"new_password": "new_secure_password"}
    res = await client.post(f"/api/admin/users/{user_id}/reset-password", json=reset_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Delete
    res = await client.delete(f"/api/admin/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Verify deleted
    res = await client.delete(f"/api/admin/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_alma_management_history_and_rollback(client: AsyncClient, admin_token, db_session):
    """Deep test of Alma prompt history and rollback mechanism."""
    # Create Alma
    payload = {
        "name": "Historian Alma",
        "description": "Historical context advisor",
        "resource_type": "ALMA",
        "alma_type": "THEORETICAL",
        "system_prompt": "Initial prompt",
        "personality_descriptor": "Formal",
        "llm_model": "llama3"
    }
    res = await client.post("/api/admin/almas", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    alma_id = res.json()["id"]

    # Update prompt
    res = await client.post(f"/api/admin/almas/{alma_id}/prompt", json={
        "new_prompt": "Updated prompt V1",
        "reason": "Clarification"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Get history
    res = await client.get(f"/api/admin/almas/{alma_id}/history", headers={"Authorization": f"Bearer {admin_token}"})
    history = res.json()
    assert len(history) == 1
    history_id = history[0]["id"]

    # Rollback
    res = await client.post(f"/api/admin/almas/{alma_id}/rollback/{history_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Verify Alma's current prompt is back to initial
    res = await client.get("/api/admin/almas", headers={"Authorization": f"Bearer {admin_token}"})
    almas = res.json()
    target_alma = next(a for a in almas if a["id"] == alma_id)
    assert target_alma["system_prompt"] == "Initial prompt"

@pytest.mark.asyncio
async def test_metrics_aggregation(client: AsyncClient, admin_token, db_session):
    """Test metrics endpoint data aggregation."""
    # Insert some dummy metrics
    metrics = [
        SystemMetric(endpoint="/api/test1", duration_ms=100, status_code=200),
        SystemMetric(endpoint="/api/test2", duration_ms=50000, status_code=200), # Slow
        SystemMetric(endpoint="/api/test3", duration_ms=200, status_code=500, error_message="Crash")
    ]
    db_session.add_all(metrics)
    await db_session.commit()

    res = await client.get("/api/admin/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    
    assert data["slow_queries_count"] >= 1
    assert any(m["endpoint"] == "/api/test3" and m["status_code"] == 500 for m in data["recent_metrics"])
    assert data["average_duration_ms"] > 0
