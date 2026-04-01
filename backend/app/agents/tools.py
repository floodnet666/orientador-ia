import logging
from typing import Optional, List, Dict, Any, Type, Annotated
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Importar serviços reais
from app.agents.state import BackendState
from app.services.hybrid_search import hybrid_search_evidence
from app.lib.tools.external_search import DeepSearchTool

log = logging.getLogger("app.agents.tools")

# --- Schemas de Entrada ---

class WhiteboardInput(BaseModel):
    field: str = Field(description="O campo estrutural a ser atualizado (tema, problema, justificativa, objetivo_geral, objetivos_especificos, metodologia_tipo, metodologia_instrumentos, mapa_mental)")
    value: str = Field(description="O conteúdo acadêmico detalhado para o campo.")

class CanvasNodeInput(BaseModel):
    id: str = Field(description="ID único e curto para o nó (ex: 'n1', 'n2')")
    label: str = Field(description="Texto visível no nó")
    type: Optional[str] = Field("PB", description="Tipo do nó: PB (Ponto de Batida), MF (Mar de Fatos), PF (Ponto de Fuga), AI (Agente Interno)")

class CanvasEdgeInput(BaseModel):
    source_id: str = Field(description="ID do nó de origem")
    target_id: str = Field(description="ID do nó de destino")
    relation: Optional[str] = Field(None, description="Texto da relação entre os nós")

class SearchInput(BaseModel):
    query: str = Field(description="Termo de pesquisa acadêmica ou científica")

# --- Implementação das Ferramentas ---

@tool("academic_search", args_schema=SearchInput)
async def academic_search(query: str) -> Dict[str, Any]:
    """
    Pesquisa literatura científica em bases globais (ArXiv, OpenAlex e SciELO).
    Use isto para encontrar novos papers, abstracts e autores relevantes que NÃO estão nos documentos do aluno.
    """
    log.info(f"LangGraph Tool: academic_search query='{query}'")
    search_tool = DeepSearchTool()
    return await search_tool.func(query)

@tool("empirical_search", args_schema=SearchInput)
async def empirical_search(
    query: str, 
    state: Annotated[BackendState, InjectedState]
) -> List[Dict[str, Any]]:
    """
    Pesquisa nos documentos carregados pelo aluno (base empírica/RAG).
    Use isto para encontrar evidências, citações e dados específicos nos PDFs do projeto.
    """
    project_id = state.get("project_id")
    log.info(f"LangGraph Tool: empirical_search query='{query}' project_id={project_id}")
    
    if not project_id:
        return [{"error": "Project ID not found in state. Certifique-se de que o projeto está carregado."}]
    
    return await hybrid_search_evidence(project_id=project_id, query=query)

@tool("update_whiteboard", args_schema=WhiteboardInput)
def update_whiteboard(field: str, value: str) -> str:
    """
    Atualiza um campo estrutural do projeto no Whiteboard Visual (Canvas).
    USE ESTA FERRAMENTA APENAS QUANDO O ALUNO ESTIVER SATISFEITO COM UM ARGUMENTO OU PARA MATERIALIZAR O PROGRESSO.
    """
    log.info(f"LangGraph Tool: update_whiteboard field={field}")
    return f"SINAL: Campo '{field}' atualizado com sucesso no Whiteboard."

@tool("add_canvas_node", args_schema=CanvasNodeInput)
def add_canvas_node(id: str, label: str, type: str = "PB") -> str:
    """
    Cria um nó visual no Whiteboard (React Flow). Útil para mapas conceituais e estruturação visual.
    TIPOS: PB (Metas/Objetivos), MF (Fatos/Citações), PF (Hipóteses), AI (Ações Agênticas).
    """
    log.info(f"LangGraph Tool: add_canvas_node id={id}, label='{label}', type={type}")
    return f"SINAL: Nó '{label}' ({id}) do tipo {type} adicionado ao Whiteboard."

@tool("add_canvas_edge", args_schema=CanvasEdgeInput)
def add_canvas_edge(source_id: str, target_id: str, relation: Optional[str] = None) -> str:
    """
    Conecta dois nós visuais no Whiteboard (React Flow) para mostrar relações lógicas.
    """
    log.info(f"LangGraph Tool: add_canvas_edge {source_id} -> {target_id}")
    return f"SINAL: Conexão criada entre {source_id} e {target_id}."

# Lista de ferramentas padrão para o orquestrador/almas
CORE_TOOLS = [
    academic_search,
    empirical_search,
    update_whiteboard,
    add_canvas_node,
    add_canvas_edge
]
