# Log de Auditoria: Refatoração LangGraph v3.0

## [28/03/2026 18:43] - Preparação e Dependências

### Alteração em: `backend/pyproject.toml`
**Motivo**: Instalação do LangGraph e resolução de conflito com `qdrant-client`.

**Removido:**
- `"qdrant-client==1.12.0"`
- `"arxiv>=2.1.3"`

**Adicionado:**
- `"qdrant-client>=1.12.0"`
- `"arxiv>=2.1.0"`
- `"langgraph>=0.2.0"`
- `"langchain-ollama>=0.2.0"`
- `"langchain-core>=0.3.0"`
- `"langchain-community>=0.3.0"`
- `"urllib3>=1.26.14"` (Injeção explícita para resolver conflito de índice)

**Contexto do Conflito:**
O `qdrant-client==1.12.0` exigia `urllib3>=1.26.14`, mas o índice do PyTorch no ambiente Windows estava forçando a versão `1.26.13`. Ao relaxar a versão do Qdrant Client, o `uv` consegue encontrar uma resolução válida compatível com o novo ecossistema LangGraph.

---

## Próximos Passos
- [ ] Validar sincronização de dependências.
- [ ] Definir o `BackendState` em `app/agents/state.py`.
