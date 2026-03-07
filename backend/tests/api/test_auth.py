import pytest
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO, filename="tests.log", filemode="w",
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants matching AcademicLevelEnum in sql_models.py
LEVEL_PHD = "PHD"
LEVEL_MASTERS = "MASTERS"
LEVEL_BACHELORS = "BACHELORS"

@pytest.mark.asyncio
async def test_register_user_success(client):
    logger.info("Starting test_register_user_success")
    register_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
        "academic_level": LEVEL_PHD
    }
    response = await client.post("/api/auth/register", json=register_data)
    logger.info(f"Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    logger.info("Starting test_register_duplicate_email")
    register_data = {
        "email": "dup@example.com",
        "password": "password",
        "full_name": "Dup User",
        "academic_level": LEVEL_MASTERS
    }
    # First registration
    await client.post("/api/auth/register", json=register_data)
    # Second registration with same email
    response = await client.post("/api/auth/register", json=register_data)
    logger.info(f"Response: {response.status_code} - {response.text}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login_success(client):
    logger.info("Starting test_login_success")
    register_data = {
        "email": "login@example.com",
        "password": "password123",
        "full_name": "Login User",
        "academic_level": LEVEL_BACHELORS
    }
    await client.post("/api/auth/register", json=register_data)
    
    login_data = {
        "email": "login@example.com",
        "password": "password123"
    }
    response = await client.post("/api/auth/login", json=login_data)
    logger.info(f"Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    logger.info("Starting test_login_invalid_credentials")
    login_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await client.post("/api/auth/login", json=login_data)
    logger.info(f"Response: {response.status_code} - {response.text}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
