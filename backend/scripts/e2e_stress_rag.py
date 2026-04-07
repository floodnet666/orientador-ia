import asyncio
import os
import sys
import time
import uuid

# Force local host config overrides for testing outside Docker
os.environ["QDRANT_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://orientador:orientador_pass@localhost:5432/orientador_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Inject backend path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import User, Project, ChatMessage, RoleEnum, AcademicLevelEnum
from app.services.empirical.document_processor import EmpiricalProcessor
from app.agents.state import BackendState
from app.state.graph_state import CanvasState, ChatMessageState, ValidationFlags
from app.agents.graph_factory import backend_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

QUESTIONS = [
    "Faça um resumo geral sobre o documento empírico referenciado no projeto.",
    "Quais são os principais conceitos teóricos abordados nesse pdf?",
    "Pode aprofundar qual é o problema de pesquisa sugerido pelo autor deste artigo?",
    "Quais são os objetivos gerais do estudo listado no documento?",
    "Descreva os objetivos específicos descritos no artigo.",
    "Que tipo de metodologia o autor utiliza?",
    "Quais autores clássicos são citados nas referências para apoiar o artigo?",
    "Há alguma relação com conceitos de campo de Bourdieu neste arquivo empírico?",
    "Onde o artigo foi originalmente publicado, segundo o documento?",
    "Como o autor justifica a relevância de sua pesquisa empírica?",
    "O artigo realiza alguma análise quantitativa ou qualitativa? Diga-me por favor baseado na busca híbrida.",
    "Liste 3 palavras cruciais que sumarizam a conclusão deste artigo.",
    "Compare a visão abordada neste artigo com metodologias pós-estruturalistas se houver menção.",
    "Qual é o título da primeira seção ou introdução do pdf, exatamente?",
    "O que significa 'redes sociais' no contexto deste artigo de modo particular?",
    "Este arquivo menciona algum estudo de caso ou recolha de dados específica?",
    "Como é feita a recolha dos dados empíricos reportados no documento?",
    "Qual a visão do autor sobre as limitações do próprio estudo?",
    "Como se processaram as fases ou secções do artigo?",
    "Há gráficos ou tabelas referenciadas no documento? Como são explicadas?",
    "Se eu aplicar esta ideia do artigo, qual seria uma justificativa excelente para minha tese?",
    "O artigo discute desigualdade social ou poder? Em que contexto?",
    "Escreve uma paráfrase densa que una o capítulo 1 e a conclusão descritos no artigo.",
    "Quais as conclusões empíricas mais inesperadas que a pesquisa encontrou?",
    "Que referências bibliográficas do artigo empírico acha que se destacam mais?",
    "Que propostas futuras o estudo deixa em aberto no capítulo final?",
    "Qual a relação do 'ator rede' com a pesquisa empírica deste ficheiro?",
    "Como esse estudo ajuda na criação de um referencial teórico forte?",
    "Resume novamente os objetivos do artigo, considerando as últimas 10 respostas discutidas.",
    "Até que ponto este RAG (você interagindo com o pdf) consegue extrair detalhes microscópicos ou está a esquecer detalhes do início deste nosso chat?"
]

async def create_mock_project() -> tuple[uuid.UUID, uuid.UUID]:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == "stress@test.com"))
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="stress@test.com",
                password_hash="mock",
                full_name="Stress Tester",
                academic_level=AcademicLevelEnum.PHD,
                is_admin=True
            )
            db.add(user)
            await db.commit()
            
        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Stress Test RAG",
            academic_level=AcademicLevelEnum.PHD
        )
        db.add(project)
        await db.commit()
        return user.id, project.id

async def ingest_document(project_id: uuid.UUID, pdf_path: str):
    print(f"[INGEST] Ingesting {pdf_path} for project {project_id}...")
    processor = EmpiricalProcessor(str(project_id), force_reindex=False)
    # The file should exist
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF {pdf_path} not found.")
        
    await processor.process_pdf_v2(pdf_path)
    print(f"[INGEST] Done.")

async def process_turn(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, question: str, i: int) -> dict:
    t0 = time.perf_counter()
    msg_user = ChatMessage(project_id=project_id, role=RoleEnum.USER, content=question)
    db.add(msg_user)
    await db.commit()
    
    # Reload DB history
    history = await db.execute(select(ChatMessage).where(ChatMessage.project_id == project_id).order_by(ChatMessage.created_at.asc()))
    history_msgs = []
    total_len_chars = 0
    for m in history.scalars().all():
        total_len_chars += len(m.content)
        if m.role == RoleEnum.USER:
            history_msgs.append(HumanMessage(content=m.content))
        elif m.role == RoleEnum.ALMA:
            history_msgs.append(AIMessage(content=m.content, name=m.alma_name or "Orientador"))
            
    # Fake Empirical Doc
    empirical_docs = [type('Doc', (), {'filename': "artigo -a.pdf", 'id': "artigo -a.pdf"})]
    
    initial_state = BackendState(
        messages=history_msgs,
        project_id=str(project_id),
        user_id=str(user_id),
        academic_level="PHD",
        active_theoretical_alma="",
        active_methodological_alma="",
        active_soul_ids=[],
        orchestrator_directive="",
        human_guidelines="",
        current_canvas=CanvasState(),
        canvas_fields_to_update={},
        validation_flags=ValidationFlags(),
        empirical_documents=empirical_docs,
        is_debate_mode=False,
        debate_round_number=0,
        debate_history=[],
        previous_debate_summary=None
    )
    
    full_response = ""
    config = {"configurable": {"thread_id": str(project_id)}}
    
    try:
        async for event in backend_graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")
                if node_name == "maestro":
                    continue
                data = event.get("data", {})
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, 'content') and chunk.content:
                    full_response += str(chunk.content)
    except Exception as e:
        print(f"[TURN {i}] WARNING - Graph Execution failed midway: {e}")
        full_response += f"\n[SYSTEM ERROR] {str(e)}"
        
    t1 = time.perf_counter()
    msg_alma = ChatMessage(project_id=project_id, role=RoleEnum.ALMA, content=full_response)
    db.add(msg_alma)
    await db.commit()
    
    return {
        "turn": i,
        "question": question,
        "answer": full_response,
        "latency_s": t1 - t0,
        "context_chars_size": total_len_chars,
        "answer_len": len(full_response)
    }

async def run_stress_test(pdf_path: str):
    user_id, project_id = await create_mock_project()
    await ingest_document(project_id, pdf_path)
    
    report_data = []
    
    async with AsyncSessionLocal() as db:
        for i, q in enumerate(QUESTIONS, 1):
            print(f"\n[{i}/30] Executing: '{q[:50]}...'")
            run_data = await process_turn(db, project_id, user_id, q, i)
            print(f"       -> Result: {run_data['answer_len']} chars in {run_data['latency_s']:.1f}s | Context pool limit approx ~{run_data['context_chars_size']} chars.")
            report_data.append(run_data)
            
    # Dump markdown report
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "docs", "audit", "stress_rag_30_turns_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# RAG Stress Testing Report (30 Turns)\n\n")
        f.write(f"**PDF**: `{pdf_path}`\n")
        f.write(f"**Date**: `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n")
        f.write("## Telemetria Geral\n")
        f.write("| Post-Turn | Context Chars | Latency (s) | Response Length |\n")
        f.write("|---|---|---|---|\n")
        for rd in report_data:
            f.write(f"| {rd['turn']} | {rd['context_chars_size']} | {rd['latency_s']:.2f} | {rd['answer_len']} |\n")
            
        f.write("\n## Histórico Transcrito (Detecção de Alucinação)\n\n")
        for rd in report_data:
            f.write(f"### Turn {rd['turn']}\n")
            f.write(f"> **Q**: {rd['question']}\n\n")
            ans = rd['answer']
            if not ans:
                ans = "*[SEM RESPOSTA - QUEBRA OU ALUCINAÇÃO NO LLM]*"
            f.write(f"**A**: {ans}\n\n")
            f.write("---\n")
            
    print(f"\n[DONE] Saved artifact to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "artigo -a.pdf"
    asyncio.run(run_stress_test(pdf_path))
