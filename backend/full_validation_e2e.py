
import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8000"

async def validate_pipeline():
    print("🚀 Inciando Validação Completa do Pipeline (E2E)...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Teste de Registro/Login
        email = f"tester_{uuid.uuid4().hex[:6]}@test.com"
        print(f"👤 [1/7] Registrando usuário: {email}")
        try:
            reg_resp = await client.post(f"{BASE_URL}/api/auth/register", json={
                "email": email,
                "password": "password123",
                "full_name": "QA Tester",
                "academic_level": "PHD"
            })
            
            if reg_resp.status_code not in [200, 201]:
                print(f"❌ Falha no registro: {reg_resp.text}")
                return
                
            token = reg_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"✅ Usuário autenticado.")
        except Exception as e:
            print(f"❌ Erro na conexão com Auth: {e}")
            return

        # 2. Criação de Projeto
        print("📁 [2/7] Criando novo projeto...")
        try:
            proj_resp = await client.post(f"{BASE_URL}/api/projects/", json={
                "title": "Projeto de Teste E2E",
                "domain_area": "Ciência de Dados",
                "academic_level": "PHD"
            }, headers=headers)
            
            if proj_resp.status_code not in [200, 201]:
                print(f"❌ Falha ao criar projeto: {proj_resp.status_code} - {proj_resp.text}")
                return
                
            project_id = proj_resp.json()["id"]
            print(f"✅ Projeto criado: {project_id}")
        except Exception as e:
            print(f"❌ Erro na criação de projeto: {e}")
            return

        # 3. Teste de Upload e Indexação (CSV)
        print("📄 [3/7] Testando Upload CSV e RAG...")
        try:
            # Using CSV which is supported
            csv_content = "tema,descricao\nFoucault,Arqueologia do Saber\nBourdieu,Poder Simbolico"
            files = {'file': ('test_e2e.csv', csv_content, 'text/csv')}
            up_resp = await client.post(f"{BASE_URL}/api/empirical/{project_id}/upload", files=files, headers=headers)
            if up_resp.status_code in [200, 201]:
                print("✅ Upload CSV bem-sucedido.")
            else:
                print(f"⚠️ Falha no upload CSV: {up_resp.status_code} - {up_resp.text}")
        except Exception as e:
            print(f"❌ Erro no upload CSV: {e}")

        # 4. Teste de Listagem de Documentos
        print("📋 [4/7] Verificando listagem de documentos...")
        try:
            list_resp = await client.get(f"{BASE_URL}/api/empirical/{project_id}/documents", headers=headers)
            if list_resp.status_code == 200:
                print(f"✅ Documentos encontrados: {list_resp.json()}")
            else:
                print(f"❌ Erro ao listar documentos: {list_resp.status_code} - {list_resp.text}")
        except Exception as e:
            print(f"❌ Erro na listagem: {e}")

        # 5. Teste de Histórico
        print("🧠 [5/7] Verificando Histórico de Chat...")
        try:
            hist_resp = await client.get(f"{BASE_URL}/api/chat/{project_id}/history", headers=headers)
            if hist_resp.status_code == 200:
                print(f"✅ Histórico recuperado.")
            else:
                print(f"❌ Erro no histórico: {hist_resp.text}")
        except Exception as e:
            print(f"❌ Erro ao buscar histórico: {e}")

        # 6. Teste de DeepSearch logic
        print("🔍 [6/7] Testando Busca Externa (DeepSearch)...")
        from app.lib.tools.external_search import DeepSearchTool
        try:
            tool = DeepSearchTool()
            res = await tool.func("Machine Learning")
            if res.get("status") == "success":
                print(f"✅ DeepSearch retornou {len(res.get('papers', []))} resultados.")
        except Exception as e:
            print(f"⚠️ Erro na busca ArXiv: {e}")

        # 7. Teste de Genesis (Criação de Alma)
        print("✨ [7/7] Testando Genesis (pode demorar)...")
        try:
            gen_resp = await client.post(f"{BASE_URL}/api/almas/genesis", json={
                "description": "Um orientador de teste especialista em epistemologia."
            }, headers=headers)
            if gen_resp.status_code in [200, 201]:
                print("✅ Alma criada via Genesis.")
            else:
                print(f"⚠️ Genesis: {gen_resp.status_code} - {gen_resp.text[:100]}")
        except Exception as e:
            print(f"❌ Erro no Genesis: {e}")

    print("\n🏁 Validação de Pipeline E2E finalizada.")

if __name__ == "__main__":
    asyncio.run(validate_pipeline())
