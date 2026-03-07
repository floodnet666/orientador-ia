import logging
import asyncio
import httpx
import arxiv
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
    MAX_RESULTS_PER_SOURCE = 2
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
                return list(client.results(search))
                
            results = await loop.run_in_executor(None, do_search)
            
            return [
                {
                    "source": "ArXiv",
                    "title": r.title,
                    "authors": [a.name for a in r.authors],
                    "published": str(r.published.date()) if r.published else "Unknown",
                    "abstract": r.summary.replace("\n", " "),
                    "url": r.pdf_url or r.entry_id
                }
                for r in results
            ]
        except Exception as e:
            log.error(f"[ArXiv] Search failed: {str(e)}")
            return []

    async def _search_openalex(self, query: str) -> List[Dict[str, Any]]:
        """Pesquisa no OpenAlex (>250M papers, equivalente livre ao Google Scholar)."""
        log.info(f"[OpenAlex] Searching for: {query}")
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                # Usa as endpoint de texto livre, limitando aos mais citados
                resp = await client.get(
                    "https://api.openalex.org/works",
                    params={
                        "search": query,
                        "per-page": self.MAX_RESULTS_PER_SOURCE,
                        "sort": "cited_by_count:desc"
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
                results = []
                for w in data.get("results", []):
                    authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
                    results.append({
                        "source": "OpenAlex",
                        "title": w.get("title", "No Title"),
                        "authors": [a for a in authors if a],
                        "published": w.get("publication_date", "Unknown"),
                        "abstract": self._reconstruct_abstract(w.get("abstract_inverted_index", {})),
                        "url": w.get("doi") or w.get("id")
                    })
                return results
        except Exception as e:
            log.error(f"[OpenAlex] Search failed: {str(e)}")
            return []

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """OpenAlex retorna um índice invertido. Precisamos recriar o abstract."""
        if not inverted_index:
            return "No abstract available."
        
        # Achar o tamanho total do abstract
        max_idx = max([max(positions) for positions in inverted_index.values() if positions])
        words = [""] * (max_idx + 1)
        
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        
        return " ".join(words).strip()

    async def _search_scielo(self, query: str) -> List[Dict[str, Any]]:
        """Pesquisa no SciELO Data/API (Literatura Ouro Latino-Americana/Ibéria)."""
        log.info(f"[SciELO] Searching for: {query}")
        try:
            # Usando a proxy pública do SciELO Search Server
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    "https://search.scielo.org/api/v1/article",
                    params={
                        "q": query,
                        "size": self.MAX_RESULTS_PER_SOURCE,
                        "sort": "year_cluster:desc" 
                    }
                )
                
                # O SciELO API pode retornar 5xx fácil, vamos ignorar silentemente as falhas,
                # mas não rebentar o pipeline inteiro de busca se acontecer
                if resp.status_code != 200:
                    log.warning(f"[SciELO] Returned non-200: {resp.status_code}")
                    return []
                    
                data = resp.json()
                results = []
                for doc in data.get("hits", {}).get("hits", []):
                    src = doc.get("_source", {})
                    title_info = src.get("ti", ["No Title"])
                    title = title_info[0] if isinstance(title_info, list) and title_info else "No Title"
                    
                    results.append({
                        "source": "SciELO",
                        "title": title,
                        "authors": src.get("au", []),
                        "published": str(src.get("year", "Unknown")),
                        "abstract": src.get("ab", ["No abstract"])[0] if isinstance(src.get("ab"), list) else "No abstract",
                        "url": f"https://search.scielo.org/search/1/document/en/{doc.get('_id', '')}"
                    })
                return results
        except Exception as e:
            log.error(f"[SciELO] Search failed: {str(e)}")
            return []

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
