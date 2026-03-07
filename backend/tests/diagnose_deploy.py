import asyncio
import sys
import os
import unittest.mock as mock

# Setup paths
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set environment for local check
os.environ["DATABASE_URL"] = "postgresql+asyncpg://orientador:orientador_pass@localhost:5432/orientador_db"

async def diagnose_db():
    print("🔍 Diagnóstico de Base de Dados...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Conexão com base de dados: SUCESSO")
            
            # Check for users
            try:
                user_count = await conn.execute(text("SELECT count(*) FROM users"))
                count = user_count.scalar()
                print(f"👥 Utilizadores registados: {count}")
            except Exception as e:
                print(f"❌ Erro ao consultar utilizadores: {e} (Tabela existe?)")
                
    except Exception as e:
        print(f"❌ Falha de conexão: {e}")
        print("\nDICA: Verifique se o contentor 'postgres' está a correr e se a porta 5432 está exposta.")

if __name__ == "__main__":
    asyncio.run(diagnose_db())
