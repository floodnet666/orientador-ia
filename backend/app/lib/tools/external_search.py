import logging
import asyncio
import httpx
import arxiv
import re
from typing import Dict, Any, List

log = logging.getLogger("tools.deep_search")

class DeepSearchTool:
    """
    Agregador de Pesquisa Profunda (Deep Search).
    Realiza buscas simultâneas em plataformas abertas (ArXiv, OpenAlex e SciELO) 
    para maximizar a diversidade e profundidade do embasamento.
    """
    
    name = "pesquisar_literatura_profunda"
    description = (
        "Pesquisa literatura científica em bases globais (OpenAlex, SciELO e ArXiv). "
        "Use isto para encontrar os Pdfs/Abstracts e autores mais relevantes para "
        "o contexto do projeto."
    )
    
    # Restrição de YAGNI: Limitar resultados por fonte para evitar context-bloat no LLM
    MAX_RESULTS_PER_SOURCE = 5
    TIMEOUT_SECONDS = 15.0

    async def _search_arxiv(self, query: str) -> List[Dict[str, Any]]:
        """Pesquisa legacy no ArXiv (Physics, Math, CS, etc)."""
        log.info(f"[ArXiv] Searching for: {query}")
        try:
            # ArXiv client is blocking, run in executor to not block the asyncio loop
            loop = asyncio.get_event_loop()
            
            def do_search():
                client = arxiv.Client()
                search = arxiv.Search(
                    query=query,
                    max_results=self.MAX_RESULTS_PER_SOURCE,
                    sort_by=arxiv.SortCriterion.Relevance
                )
                results = list(client.results(search))
                papers = []
                for r in results:
                    summary = r.summary.replace("\n", " ")
                    links = re.findall(r'http[s]?://[^\s<>"]+|(?<=ref=")[^"]+', summary)
                    
                    pdf_url = None
                    landing_url = r.entry_id
                    
                    for lnk in links:
                        if "arxiv.org/pdf/" in lnk:
                            pdf_url = lnk
                        elif "doi.org" in lnk or "arxiv.org/abs/" in lnk:
                            landing_url = lnk
                    
                    if not pdf_url and landing_url and "arxiv.org/abs/" in landing_url:
                        paper_id = landing_url.split("/")[-1]
                        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
                    elif not pdf_url and landing_url and "/abs/" in landing_url:
                        paper_id = landing_url.split("/")[-1]
                        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
                        
                    papers.append({
                        "source": "ArXiv [v10.1]",
                        "title": r.title,
                        "authors": [a.name for a in r.authors],
                        "published": str(r.published.date()) if r.published else "Unknown",
                        "abstract": summary,
                        "pdf_url": pdf_url,
                        "landing_url": landing_url,
                        "url": landing_url
                    })
                return papers
                
            return await loop.run_in_executor(None, do_search)
        except Exception as e:
            log.error(f"[ArXiv] Search failed: {str(e)}")
            return []

    async def _search_openalex(self, query: str, scielo_only: bool = False) -> List[Dict[str, Any]]:
        """Pesquisa no OpenAlex (>250M papers, equivalente livre ao Google Scholar)."""
        source_label = "SciELO (via OpenAlex)" if scielo_only else "OpenAlex"
        log.info(f"[{source_label}] Searching for: {query}")
        
        headers = {
            "User-Agent": "OrientadorIA/1.0 (mailto:admin@orientadoria.pt)"
        }
        
        try:
            params = {
                "search": query,
                "per-page": self.MAX_RESULTS_PER_SOURCE,
                "sort": "cited_by_count:desc"
            }
            if scielo_only:
                # Filter specifically for Open Access (SciELO characteristic) 
                # and try to find scielo in the locations
                params["filter"] = "is_oa:true"

            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS, headers=headers) as client:
                resp = await client.get("https://api.openalex.org/works", params=params)
                resp.raise_for_status()
                data = resp.json()
                
                results = []
                for w in data.get("results", []):
                    if scielo_only:
                        # Double check if scielo is in one of the host venues
                        locations = w.get("locations") or []
                        is_scielo = any(
                            loc and "scielo" in str(loc.get("source", {}).get("display_name", "")).lower() 
                            for loc in locations
                        )
                        if not is_scielo and query.lower() not in str(w.get("title", "")).lower():
                            continue

                    # Extração de Links Reais (PDF vs Landing)
                    oa_data = w.get("best_oa_location") or {}
                    pdf_url = oa_data.get("pdf_url")
                    landing_url = w.get("doi") or oa_data.get("landing_page_url") or w.get("id")

                    # Validação heurística de PDF: se não terminar em .pdf ou não conter /pdf/ no path, 
                    # e for o mesmo link da landing, provavelmente não temos o binário direto.
                    if pdf_url and pdf_url == landing_url:
                        if not (pdf_url.lower().endswith(".pdf") or "/pdf/" in pdf_url.lower() or "/view/" in pdf_url.lower()):
                            pdf_url = None

                    results.append({
                        "source": source_label,
                        "title": w.get("title", "No Title"),
                        "authors": [
                            a.get("author", {}).get("display_name", "") 
                            for a in (w.get("authorships") or []) 
                            if a and isinstance(a, dict) and a.get("author")
                        ],
                        "published": w.get("publication_date", "Unknown"),
                        "abstract": self._reconstruct_abstract(w.get("abstract_inverted_index") or {}),
                        "pdf_url": pdf_url,
                        "landing_url": landing_url,
                        "url": landing_url # Legacy compatibility
                    })
                return results
        except Exception as e:
            log.error(f"[{source_label}] Search failed: {str(e)}")
            return []

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """OpenAlex retorna um índice invertido. Precisamos recriar o abstract."""
        if not inverted_index or not isinstance(inverted_index, dict):
            return "No abstract available."
        
        try:
            # Achar o tamanho total do abstract
            all_positions = [pos for positions in inverted_index.values() for pos in (positions or [])]
            if not all_positions:
                return "No abstract available."
                
            max_idx = max(all_positions)
            words = [""] * (max_idx + 1)
            
            for word, positions in inverted_index.items():
                for pos in (positions or []):
                    if pos <= max_idx:
                        words[pos] = word
            
            return " ".join(words).strip()
        except (ValueError, TypeError) as e:
            log.warning(f"Failed to reconstruct abstract: {str(e)}")
            return "Abstract reconstruction failed."

    async def _search_scielo(self, query: str) -> List[Dict[str, Any]]:
        """Pesquisa no SciELO (Literatura Ouro Latino-Americana/Ibéria) via OpenAlex."""
        return await self._search_openalex(query, scielo_only=True)

    async def func(self, query: str) -> Dict[str, Any]:
        """
        Executa as três buscas concorrentemente para máxima eficiência termodinâmica.
        """
        log.info(f"Initiating Deep Search across all sources for: '{query}'")
        
        # Parallel Execution Map
        arxiv_task = self._search_arxiv(query)
        openalex_task = self._search_openalex(query)
        scielo_task = self._search_scielo(query)
        
        # Resolvendo promessas simutâneinamente - YAGNI: Se der erro num deles, prossegue.
        results_tuple = await asyncio.gather(
            arxiv_task, openalex_task, scielo_task, 
            return_exceptions=True
        )
        
        arxiv_res = results_tuple[0] if not isinstance(results_tuple[0], Exception) else []
        openalex_res = results_tuple[1] if not isinstance(results_tuple[1], Exception) else []
        scielo_res = results_tuple[2] if not isinstance(results_tuple[2], Exception) else []
        
        combined_results = arxiv_res + openalex_res + scielo_res
        
        if not combined_results:
            return {
                "status": "success",
                "message": "A pesquisa não encontrou resultados em nenhuma das fontes.",
                "papers": []
            }

        return {
            "status": "success",
            "query": query,
            "total_papers_found": len(combined_results),
            "papers": combined_results
        }
