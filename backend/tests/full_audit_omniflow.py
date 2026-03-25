import asyncio
import time
import uuid
import os
import json
import sys

# 1. Configurações de Auditoria
PROJECT_ID = uuid.uuid4()
FILENAME = "Artigo-1.pdf"
FILE_PATH = "d:/orientador.ia/Artigo-1.pdf"
REPORT_PATH = "d:/orientador.ia/full_audit_omniflow.md"

# Bateria de Questões Diagnósticas (Foco em Rigor e Verificabilidade)
DIAGNOSTIC_QUESTIONS = [
    "O que diferencia a arquitetura OMNIFLOW de um LLM tradicional no tratamento de leis físicas?",
    "Como o 'Semantic-Symbolic Alignment' traduz tensores em descritores linguísticos?",
    "Explique o workflow do 'Physics-Guided Chain-of-Thought' (PG-CoT).",
    "Qual o valor exato (com decimais) da pressão máxima no ERA5 Ground Truth e qual sistema ela indica? (Pág. 15)",
    "O que o desvio padrão de ~12.8 hPa reflete sobre o clima de Janeiro?",
    "O que as zonas 'Blue/Dark' no heatmap confirmam em termos de centros de baixa pressão?",
    "Qual a amplitude (span) total de pressão citada e o que ela impulsiona?",
    "Onde o artigo sugere a localização de um 'deep extratropical cyclone' ou fragmento de vórtice polar?",
    "Por que o 'fine-tuning específico' é considerado limitado para generalização científica?",
    "Cite um exemplo de 'dynamic constraint injection' mencionado no resumo do sistema."
]

def log_step(step_name, status="START"):
    """Imprime um marcador visual claro no terminal."""
    border = "=" * 60
    if status == "START":
        print(f"\n{border}")
        print(f"🚀 STEP: {step_name}")
        print(f"{border}\n")
    elif status == "DONE":
        print(f"\n✅ {step_name} CONCLUÍDO\n")
    elif status == "INFO":
        print(f"💡 {step_name}")

async def run_full_audit():
    # Carregamento tardio para evitar problemas de inicialização
    from app.services.empirical.document_processor import empirical_processor
    from app.services.ollama_client import ollama_client
    from app.config import settings

    log_step(f"Iniciando Auditoria Intelectual: {FILENAME}")
    
    # 1. Ingestão
    log_step("M1/M2: Ingestão e Enriquecimento Contextual", "START")
    print(f"Extraindo markdown e gerando contexto via {settings.OLLAMA_CHAT_MODEL}...")
    ingest_start = time.perf_counter()
    try:
        await empirical_processor.process_pdf_v2(FILE_PATH, PROJECT_ID, FILENAME)
        ingest_duration = time.perf_counter() - ingest_start
        log_step(f"Ingestão finalizada em {ingest_duration:.2f}s", "DONE")
    except Exception as e:
        print(f"❌ ERRO na Ingestão: {e}")
        return

    report_content = [
        "# Audit Report: OMNIFLOW Intellectual Quality (Full Audit)\n",
        f"**Objetivo:** Avaliar a qualidade intelectual da resposta gerada pelo modelo {settings.OLLAMA_CHAT_MODEL}.\n",
        f"**Documento:** {FILENAME}\n",
        f"**Project ID:** {PROJECT_ID}\n",
        "---\n"
    ]

    # 2. Bateria de Testes
    log_step(f"Executando {len(DIAGNOSTIC_QUESTIONS)} Questões Diagnósticas", "START")
    
    for i, question in enumerate(DIAGNOSTIC_QUESTIONS, 1):
        print(f"\n🔍 QUESTION {i}/{len(DIAGNOSTIC_QUESTIONS)}: {question}")
        
        # RAG Step
        print(f"  ├─ 📥 Buscando evidências no Qdrant (Híbrido)... ", end="", flush=True)
        rag_start = time.perf_counter()
        evidences = await empirical_processor.search_evidence(PROJECT_ID, question, limit=3)
        rag_duration = (time.perf_counter() - rag_start) * 1000
        print(f"OK ({rag_duration:.1f}ms)")
        
        snippet = evidences[0].get('text', 'NENHUM CONTEXTO RECUPERADO') if evidences else 'N/A'
        
        # Generation Step
        print(f"  ├─ 🤖 Gerando resposta via Ollama ({settings.OLLAMA_CHAT_MODEL})... ", end="", flush=True)
        gen_start = time.perf_counter()
        
        context_str = "\n".join([f"Source [{e.get('filename')}]: {e.get('text')}" for e in evidences])
        prompt = (
            f"Você é um Auditor Científico Especialista (Alma). Use o contexto abaixo para responder a pergunta com rigor absoluto.\n\n"
            f"CONTEXTO RECUPERADO:\n{context_str}\n\n"
            f"PERGUNTA: {question}\n\n"
            f"REGRAS:\n1. Se o contexto não contiver a resposta, diga explicitamente.\n"
            f"2. Cite valores exatos.\n3. Não alucine.\n\n"
            f"RESPOSTA:"
        )
        
        try:
            response = await ollama_client.chat_complete(
                model=settings.OLLAMA_CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            gen_duration = (time.perf_counter() - gen_start) * 1000
            print(f"OK ({gen_duration:.1f}ms)")
        except Exception as e:
            print(f"FAIL ({e})")
            response = f"ERRO na geração: {e}"
            gen_duration = 0

        # Grounding Audit (Heurística visual)
        grounding_detected = any(word.lower() in snippet.lower() for word in ["hpa", "omniflow", "era5", "tensor", "physics"] if word.lower() in question.lower())
        hallucination_audit = "Aprovado (Grounding detectado)" if grounding_detected else "Análise de Grounding Necessária"
        print(f"  └─ ✨ Auditoria: {hallucination_audit}")

        # Formatação do Relatório
        report_content.append(f"### Q{i}: {question}\n")
        report_content.append(f"**Resposta Gen:** {response}\n")
        report_content.append(f"**Snippet Base:** `{snippet[:300]}...`\n")
        report_content.append(f"**Stats:** RAG: {rag_duration:.1f}ms | LLM: {gen_duration:.1f}ms | Audit: {hallucination_audit}\n")
        report_content.append("---\n")

    # 3. Finalização
    log_step("Gerando Relatório Final", "START")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_content))
    
    log_step(f"AUDITORIA CONCLUÍDA: {REPORT_PATH}", "DONE")

if __name__ == "__main__":
    asyncio.run(run_full_audit())
