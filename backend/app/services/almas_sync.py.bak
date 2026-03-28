import logging
from app.models.sql_models import EcosystemResource
from app.services.qdrant_service import index_alma
from app.agents.almas.base_alma import register_alma, StatelessAlma
from app.models.agent_config import AgentConfig, AgentTool

log = logging.getLogger("almas.sync")

async def sync_alma_to_system(alma: EcosystemResource) -> bool:
    """
    Sincroniza uma Alma (EcosystemResource) com o motor de busca (Qdrant)
    e com a memória ativa do servidor (ADK Registry).
    Ensina o sistema a reconhecer a nova alma imediatamente sem restart.
    """
    try:
        # 1. Indexação no Qdrant para o Match Engine
        await index_alma(alma)
        log.info(f"Alma '{alma.name}' indexada no Qdrant com sucesso.")
        
        # 2. Registro na Memória Ativa (Hot-reload)
        # Ferramentas padrão habilitadas para novas almas
        default_tools = [
            AgentTool(name="openalex_search", enabled=True),
            AgentTool(name="rag_query", enabled=True),
            AgentTool(name="canvas_write", enabled=True)
        ]
        
        config = AgentConfig(
            id=str(alma.id),
            name=alma.name,
            persona_description=alma.description or "",
            system_prompt=alma.system_prompt or "",
            epistemological_stance="Custom Sync",
            conflict_patterns=[],
            tools=default_tools
        )
        
        register_alma(StatelessAlma(config))
        log.info(f"Alma '{alma.name}' (ID: {alma.id}) registrada na memória ativa com sucesso.")
        
        return True
    except Exception as e:
        log.error(f"Erro fatal ao sincronizar Alma '{alma.name}': {e}")
        return False
