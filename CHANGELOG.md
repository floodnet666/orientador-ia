## [2026-04-01] - v9.1.0 - Universalização da Identidade e Persistência do Gênesis
Implementação do protocolo de rigor acadêmico para o Modo Debate, eliminando placeholders genéricos e automatizando a expansão do catálogo de especialistas.

### ADICIONADO:
- **Gênesis de Emergência (Rigor 80%)**: Em `graph_factory.py`, injetado check de aderência semântica. Se o catálogo não prover match > 80%, o sistema gera uma Alma *ad hoc*.
- **Persistência Automática**: Almas geradas via Gênesis são agora salvas permanentemente em `ecosystem_resources` (`is_approved=True`, `scope=GLOBAL`), tornando o ecossistema auto-expansível.
- **Identidade Dinâmica (Sincronia Total)**: Refatorado `chat.py` e `alma_registry.py` para resolver identidades via `panel` dinâmico em vez de registros estáticos.
    - O frontend agora exibe nomes reais (ex: Foucault) desde o `debate_manifest` inicial.
- **Injeção de Personalidade (Léxico)**: Em `debate_subgraph.py`, o prompt de cada Alma agora recebe diretrizes de estilo e personalidade (`custom_instructions`), garantindo fidelidade autoral.

### REMOVIDO:
- Removidos nomes estáticos "Alma Primária", "Complementar" e "Antagonista" do `alma_registry.py`. Agora o sistema utiliza `[Pendente]` como fallback seguro até a resolução do painel.

### CORRIGIDO:
- **WebSocket Identity Race**: Resolvido problema em que o frontend exibia nomes genéricos no primeiro turno por falta de metadados no manifesto inicial.
- **UUID Persistence Error**: Garantida a conversão de `UUID` para `string` nos payloads do WebSocket para compatibilidade com Zod no frontend.
- **Hotfix (v9.1.1)**: Corrigido `NameError: Optional is not defined` em `alma_registry.py` através da importação correta dos tipos `Optional` e `Any` do módulo `typing`.


---

