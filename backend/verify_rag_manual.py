
import asyncio
import uuid
from app.services.empirical.document_processor import empirical_processor
from app.services.ollama_client import ollama_client

async def verify_rag_pipeline():
    project_id = uuid.uuid4()
    filename = "test_document.txt"
    content = "A Arqueologia do Saber é uma obra de Michel Foucault que trata sobre a análise dos sistemas de pensamento e conhecimento."
    
    print(f"🚀 Iniciando teste de RAG para o projeto: {project_id}")
    
    # 1. Indexar documento
    try:
        print(f"📄 Indexando conteúdo: {content[:50]}...")
        await empirical_processor.index_document(project_id, filename, content)
        print("✅ Documento indexado com sucesso.")
    except Exception as e:
        print(f"❌ Erro na indexação: {e}")
        return

    # 2. Pesquisar
    query = "O que trata a Arqueologia do Saber?"
    print(f"🔍 Pesquisando por: '{query}'")
    try:
        results = await empirical_processor.search_evidence(project_id, query)
        if results:
            print(f"✅ Resultados encontrados ({len(results)}):")
            for res in results:
                print(f" - [{res['filename']}] (Score: {res['score']:.4f}): {res['text'][:100]}...")
        else:
            print("⚠️ Nenhum resultado encontrado.")
    except Exception as e:
        print(f"❌ Erro na pesquisa: {e}")

if __name__ == "__main__":
    asyncio.run(verify_rag_pipeline())
