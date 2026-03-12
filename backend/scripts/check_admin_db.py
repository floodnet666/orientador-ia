import asyncio
import sys
import os

from sqlalchemy import select
from passlib.context import CryptContext

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.sql_models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_auth():
    print("running auth check...")
    emails_to_test = ["thiagofloodnet", "thiagofloodnet@hotmail.com"]
    password = "pimpe281"
    
    async with AsyncSessionLocal() as db:
        for email in emails_to_test:
            print(f"--- Checking email: {email} ---")
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"User FOUND: id={user.id}, is_admin={user.is_admin}")
                is_valid = pwd_context.verify(password, user.password_hash)
                print(f"Password '{password}' valid? {is_valid}")
            else:
                print("User NOT FOUND.")

if __name__ == "__main__":
    asyncio.run(test_auth())
