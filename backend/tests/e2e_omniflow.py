import asyncio
import time
import uuid
import os
import json
from app.services.empirical.document_processor import empirical_processor
# Removed pandas to eliminate environment friction

# Configurações do Teste OMNIFLOW v2.2.0
PROJECT_ID = uuid.uuid4()
FILENAME = "Artigo-1.pdf"
FILE_PATH = "d:/orientador.ia/Artigo-1.pdf"
REPORT_PATH = "backend/test_report_omniflow.md"

TEST_QUERIES = [
    "Qual é o objetivo principal do sistema OmniFlow?",
    "Quais são os componentes principais da arquitetura?",
    "Como o sistema lida com a pressão de 1045.94 hPa?",
    "O que o SPLADE faz com o termo 'Educação'?",
    "Qual a vantagem do re-ranking condicional?",
    "Como o Redis é usado na ingestão?",
    "Quais as conclusões sobre a latência?",
    "O sistema suporta múltiplos documentos?",
    "Como a normalização Unicode ajuda na busca?",
    "O que significa 'Source Attribution' na v2.2.0?"
]

async def run_omniflow_test():
    report_lines = ["# Test Report: OMNIFLOW (RAG v2.2.0 Validation)\n"]
    
    print(f"--- 1. Ingestão ---")
    start_total = time.perf_counter()
    await empirical_processor.process_pdf_v2(FILE_PATH, PROJECT_ID, FILENAME)
    ingest_duration = time.perf_counter() - start_total
    
    report_lines.append(f"## 3.1 Relatório de Ingestão")
    report_lines.append(f"- Tempo Total: {ingest_duration:.2f}s")
    report_lines.append(f"- Status Contextual: Sucesso\n")

    print(f"--- 2. Bateria de Query ---")
    report_lines.append("## 3.2 Tabela de Resultados\n")
    report_lines.append("| ID | Pergunta | Reranked? | Latência (ms) | Grounding |")
    report_lines.append("|---|---|---|---|---|")

    for i, query in enumerate(TEST_QUERIES, 1):
        q_start = time.perf_counter()
        results = await empirical_processor.search_evidence(PROJECT_ID, query)
        q_duration = (time.perf_counter() - q_start) * 1000
        
        reranked = "Sim" if results and results[0].get('rerank_score') else "Não"
        source = results[0].get('source_title', 'N/A') if results else 'N/A'
        
        report_lines.append(f"| {i} | {query} | {reranked} | {q_duration:.2f} | {source} |")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Relatório gerado em {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_omniflow_test())
