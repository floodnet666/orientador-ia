import pytest
import asyncio
import httpx
import logging
from app.lib.tools.external_search import DeepSearchTool

# Configuração de Logs para auditoria
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test.download_audit")

@pytest.mark.asyncio
class TestDownloadLinksAudit:
    """
    Suíte de Auditoria Técnica (v10) para verificação de links reais e download efetivo.
    Aplica princípios de XP e TDD para garantir zero alucinação bibliográfica.
    """
    
    @pytest.fixture
    def tool(self):
        return DeepSearchTool()

    async def _verify_link(self, url: str, is_pdf: bool = False):
        """Helper para verificar se um link é real e funcional."""
        if not url:
            return False, "Link Ausente"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(url)
                
                # [Rigor Auditor] Distinguir Falha Física de Alucinação
                if resp.status_code == 404:
                    return False, "404 - ALUCINAÇÃO (Link não existe)"
                if resp.status_code == 403:
                    return True, "200/403 - REAL (Acesso Restrito pelo Repositório)"
                if resp.status_code >= 400:
                    return False, f"Erro HTTP {resp.status_code}"
                
                if is_pdf:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    # ArXiv PDFs podem retornar application/pdf ou octet-stream
                    is_valid_pdf = "application/pdf" in content_type or resp.content.startswith(b"%PDF")
                    if not is_valid_pdf and resp.status_code == 200:
                        return False, f"Não é binário PDF (Type: {content_type})"
                
                return True, "OK"
        except httpx.ConnectError:
            return False, "Erro de Conexão (Domínio Inexistente - ALUCINAÇÃO)"
        except Exception as e:
            return False, str(e)

    @pytest.mark.parametrize("theme, query, expected_source", [
        ("Física (EN)", "Quantum Entanglement Einstein Podolsky Rosen", "ArXiv"),
        ("Psicologia (PT-BR)", "Psicopatologia do Trabalho Saúde Mental", "SciELO (via OpenAlex)"),
        ("Sociologia (PT-BR)", "Desigualdade Social e Pobreza no Brasil", "SciELO (via OpenAlex)"),
        ("Interseção (EN/PT-BR)", "Donna Haraway Cyborg Manifesto Critical Theory", "OpenAlex")
    ])
    async def test_academic_links_validity(self, tool, theme, query, expected_source):
        """
        [MODO RELATÓRIO v10.2] 
        Executa a busca e gera um relatório Markdown para auditoria manual.
        """
        log.info(f"\n[AUDIT] Testando Tema: {theme} | Query: '{query}'")
        
        result = await tool.func(query=query)
        assert result["status"] == "success"
        papers = result.get("papers", [])
        
        assert len(papers) > 0, f"Nenhum paper encontrado para {theme}"
        
        # --- RELATÓRIO DE AUDIT ---
        report = []
        report.append(f"\n### 📊 Relatório de Auditoria: {theme}")
        report.append(f"**Query:** `{query}` | **Fonte Principal:** {expected_source}\n")
        report.append("| Paper Title | Landing Page | Download PDF | Status |")
        report.append("| :--- | :--- | :--- | :--- |")
        
        failing_papers = [] # Somente alucinações críticas (404)
        
        for paper in papers:
            title = paper.get("title", "Unknown")
            pdf_url = paper.get("pdf_url")
            landing_url = paper.get("landing_url") or paper.get("url")
            
            # 1. Verificar Links
            ok_landing, msg_landing = await self._verify_link(landing_url)
            
            pdf_status = "N/A"
            if pdf_url:
                await asyncio.sleep(0.3)
                ok_pdf, msg_pdf = await self._verify_link(pdf_url, is_pdf=True)
                pdf_status = msg_pdf if not ok_pdf else "✅ OK"
                if not ok_pdf and "404" in msg_pdf:
                    failing_papers.append(f"{title} (PDF 404)")
            
            # Formatação do Relatório
            status_cell = "✅ VERIFICADO" if ok_landing else f"❌ {msg_landing}"
            if "403" in msg_landing or "403" in pdf_status:
                status_cell = "🔐 RESTRICTED (REAL)"
                
            report.append(f"| {title[:60]}... | [Link]({landing_url}) | [PDF]({pdf_url or '#'}) | {status_cell} ({pdf_status}) |")

            if not ok_landing and "404" in msg_landing:
                failing_papers.append(f"{title} (Landing 404)")

        # --- SIMULAÇÃO DE OUTPUT DA ALMA ---
        report.append("\n#### 🤖 Simulação de Citação (Protocolo Alma v10):")
        example_paper = papers[0]
        cite_link = example_paper.get('pdf_url') or example_paper.get('landing_url')
        report.append(f"> \"De acordo com a pesquisa em {theme}, o estudo '{example_paper['title']}' demonstra que... [Download/Link]({cite_link})\"")
        
        # Print do relatório para o usuário ler no terminal (pytest -s)
        print("\n".join(report))
        
        if failing_papers:
            pytest.fail(f"ALUCINAÇÃO DETECTADA em {theme}:\n" + "\n".join(failing_papers))
        
        log.info(f"  [SUCCESS] {theme} auditado. Verifique os links acima manualmente.")

    async def test_llm_markdown_output_simulation(self, tool):
        """
        [Audit Phase 2] Simula a recepção de dados e verifica se há links para a LLM processar.
        (Nesta fase RED, verificamos se as chaves necessárias existem).
        """
        result = await tool.func(query="Black Holes")
        papers = result.get("papers", [])
        
        # Atualmente o DeepSearchTool NÃO tem 'pdf_url' para OpenAlex, deve falhar aqui.
        for p in papers:
            if "ArXiv" in p["source"]:
                continue # ArXiv já tenta pdf_url
            
            # OpenAlex deve falhar na fase RED pois não mapeamos best_oa_location ainda
            assert "pdf_url" in p, f"Paper de {p['source']} sem chave pdf_url"
            assert "landing_url" in p, f"Paper de {p['source']} sem chave landing_url"
