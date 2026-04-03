import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Ajuste do path para importar os models corretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.project import Project
from app.core.security import get_password_hash

DATABASE_URL = "postgresql+asyncpg://orientador:orientador_pass@postgres:5432/orientador_db"

async def seed_recovery():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Verificar se usuário já existe
        result = await session.execute(select(User).where(User.email == "thiagofloodnet@hotmail.com"))
        user = result.scalar_one_or_none()

        if not user:
            print("Creating admin user...")
            user = User(
                full_name="Thiago Auditor",
                email="thiagofloodnet@hotmail.com",
                hashed_password=get_password_hash("Password123!"),
                is_active=True,
                is_admin=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # 2. Criar projeto
        print("Creating project context...")
        project = Project(
            title="Precarização do Trabalho na Era da IA",
            description="Projeto de pesquisa sobre impactos da IA e algoritmos na saúde mental e precarização digital.",
            owner_id=user.id
        )
        session.add(project)
        await session.commit()
        
        print(f"Restoration Complete. User: {user.email}, Project ID: {project.id}")

if __name__ == "__main__":
    asyncio.run(seed_recovery())
