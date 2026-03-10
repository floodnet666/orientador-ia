import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import User, AcademicLevelEnum
from app.api.auth import hash_password

async def setup_admin():
    email = "thiagofloodnet@hotmail.com"
    password = "pimpe281"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"User {email} already exists. Updating to Admin...")
            user.password_hash = hash_password(password)
            user.is_admin = True
        else:
            print(f"Creating new Admin user: {email}")
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name="Admin",
                academic_level=AcademicLevelEnum.PHD,
                is_admin=True
            )
            db.add(user)
        
        await db.commit()
        print(f"SUCCESS: Admin {email} configured.")

if __name__ == "__main__":
    asyncio.run(setup_admin())
