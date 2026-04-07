import pytest
from unittest.mock import AsyncMock, patch
from app.agents.graph_factory import debate_node
from app.models.sql_models import EcosystemResource, ResourceTypeEnum, AlmaTypeEnum, ScopeEnum
from app.agents.state import BackendState
from app.state.graph_state import CanvasState
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import Base

# Setup de DB In-Memory para Teste de Rigor
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL)
AsyncSessionTest = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.mark.asyncio
async def test_debate_panel_generation_scenarios():
    """Valida a lógica de 1 a 4 almas e evocação do DB."""
    
    # 1. Preparar o banco de teste
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionTest() as db:
        # Patch da fonte real do AsyncSessionLocal para interceptar todas as chamadas no grafo
        with patch("app.database.AsyncSessionLocal", side_effect=lambda: db):
            with patch("app.services.genesis_service.genesis_service.generate_alma") as mock_genesis:
                mock_genesis.side_effect = lambda desc: {
                    "name": f"Alma Gerada {desc[:10]}",
                    "description": "Gênesis Teste",
                    "system_prompt": "Prompt Teste"
                }

                # --- CENÁRIO 1: 1 Alma Ativa (Ex: Foucault) ---
                state_1 = {
                    "messages": [{"role": "user", "content": "Quero debater foucault"}],
                    "active_theoretical_alma": "Michel Foucault",
                    "active_soul_ids": ["foucault-uuid"],
                    "canvas_nodes": []
                }
                
                # O debate_node chama analyze_context interna. Vamos mockar o analyze_context para focar no node
                from app.agents.debate.context_analyzer import DebateContext
                mock_ctx = DebateContext(
                    project_id="test", canvas={}, user_message="Quero debater", 
                    debate_intent="FREE_DEBATE", academic_level="PHD"
                )
                
                with patch("app.agents.debate.context_analyzer.analyze_context", return_value=mock_ctx):
                    # Forçamos o panel_selector a não encontrar almas no DB inicialmente
                    with patch("app.agents.debate.panel_selector.select_panel") as mock_selector:
                        from app.agents.debate.panel_selector import SelectedPanel, RoleSelection
                        # Painel simulando 1 ativa e 3 com score baixo para forçar Gênesis
                        mock_selector.return_value = SelectedPanel(
                            PRIMARIA=RoleSelection(alma_name="Foucault", score=1.0),
                            COMPLEMENTAR=RoleSelection(alma_name="Desconhecido", score=0.5), # < 0.8
                            ANTAGONISTA=RoleSelection(alma_name="Desconhecido", score=0.5),  # < 0.8
                            METODOLOGICA=RoleSelection(alma_name="Desconhecido", score=0.5)  # < 0.8
                        )
                        
                        # Mock da execução do subgrafo para não gastar tokens
                        with patch("app.lib.graph.subgraphs.debate_subgraph.debate_subgraph.ainvoke", return_value={"synthesis": "OK", "turns": []}):
                            await debate_node(state_1)
                            
                            # Verificação: Gênesis deve ter sido chamado 3 vezes (Complementar, Antagonista, Metodológica)
                            assert mock_genesis.call_count == 3
                            print("\n✅ Cenário 1: 3 Gênesis disparados com sucesso.")

                # --- CENÁRIO 2: Almas Aderentes no DB ---
                mock_genesis.reset_mock()
                # Adicionamos uma alma aderente ao DB
                nova_alma = EcosystemResource(
                    resource_type=ResourceTypeEnum.ALMA, name="Adorno", 
                    description="Teoria Crítica", system_prompt="...",
                    is_approved=True, scope=ScopeEnum.GLOBAL
                )
                db.add(nova_alma)
                await db.commit()
                
                with patch("app.agents.debate.context_analyzer.analyze_context", return_value=mock_ctx):
                    with patch("app.agents.debate.panel_selector.select_panel") as mock_selector:
                        # Simulamos que o seletor achou Adorno no DB com score 0.9
                        mock_selector.return_value = SelectedPanel(
                            PRIMARIA=RoleSelection(alma_name="Foucault", score=1.0),
                            COMPLEMENTAR=RoleSelection(alma_name="Adorno", score=0.9), # > 0.8
                            ANTAGONISTA=RoleSelection(alma_name="Desconhecido", score=0.5), 
                            METODOLOGICA=RoleSelection(alma_name="Desconhecido", score=0.5)
                        )
                        
                        with patch("app.lib.graph.subgraphs.debate_subgraph.debate_subgraph.ainvoke", return_value={"synthesis": "OK", "turns": []}):
                            await debate_node(state_1)
                            # Verificação: Gênesis deve ter sido chamado apenas 2 vezes (Antagonista e Metodológica)
                            # Adorno foi evocado do DB.
                            assert mock_genesis.call_count == 2
                            print("✅ Cenário 3: Evocação do DB respeitada (Menos Gênesis).")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_debate_panel_generation_scenarios())
