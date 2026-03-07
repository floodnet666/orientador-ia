# Orientador.IA - Changelog

Forçando as "Regras YAGNI", "SOLID", e Zero Bloat conforme requisitado pelo Orientador.IA.

## [2026-03-06] - Implementação de Deep Search
A arquitetura base (Mock-Driven) usada para testes locais foi trocada por acessos em *Runtime* real.

### REMOVIDO:
- Removido `arxiv` SDK (Devido a falhas de compatibilidade com dependências nativas e bloat da libraria `requests`).
- Removido qualquer menção a *mocks*, ou listas hardcoded em `tests`. O sistema usa puramente I/O real agora.

### ADICIONADO:
- **`DeepSearchTool`**: Criada versão ultra-rápida do agregador de pesquisa em `app/lib/tools/external_search.py`.
    - Utiliza `httpx.AsyncClient` + `asyncio.gather` para paralelizar as procuras sem atrasar o loop do `fastapi`.
    - Integrado o **OpenAlex API** para busca em >250M de referências, ultrapassando os bloqueios anti-bot do Google Scholar.
    - Integrado o **SciELO API** para reforçar pesquisas em língua Portuguesa e Ibero-Americana.
    - O ArXiv foi mantido, mas com limitadores de *output* por fonte, para não saturar os tokens do LLM `qwen3.5:4b` na fase de "Thinking" ou contexto primário.
- **`BaseAlma` Update**: A ferramenta `ExternalPaperSearchTool` foi descartada e a `DeepSearchTool` foi adicionada e instruída explicitamente para reportar no WebSocket.
- **Testes de Integração REAIS**: `test_deep_search.py` a bater sem Mocks nos domínios do OpenAlex, SciELO e ArXiv com sucesso. Verificado que regressões de rede disparam "grace fails", mantendo The Happy Path sempre protegido pelas rotinas Try/Catch.
