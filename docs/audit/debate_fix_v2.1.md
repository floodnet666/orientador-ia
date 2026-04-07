# Auditoria de Alteração: Debate Pipeline v2.1.0

> **Propósito:** Documentar migração do contrato de DebateContext e Gênesis de Emergência.
> **Padrão de Backup:** `context_analyzer_v2.py`, `graph_factory_v2.py`.

---

## 1. Localização: `app/agents/debate/context_analyzer.py`

### O que foi REMOVIDO:
- Assinatura rígida `analyze_context(state: GraphState, ...)`.
- Acesso por atributos direto (`state.current_canvas.tema`) — incompatível com `TypedDict`.
- Instanciação de `DebateContext` sem `project_id`, `academic_level` e `debate_intent`.
- `raise exc` no `analyze_context`, que causava crash total do pipeline se o LLM falhasse.

### O que foi ADICIONADO:
- Helper `_get(obj, key)` para extração polimórfica (suporta `dict` e `object`).
- Sanitização de `previous_debate_summary` (conversão de JSON str se necessário).
- Conversão explícita de `CanvasState` (Pydantic) para `dict` via `model_dump()`.
- Fallback seguro para `intent = "FREE_DEBATE"` em caso de falha crítica do LLM.
- Adição de `project_id`, `academic_level` e `round_number` na criação do `DebateContext`.

---

## 2. Localização: `app/agents/graph_factory.py`

### O que foi REMOVIDO:
- Instanciação manual simplificada de `DebateContext` no `debate_node`.
- Acesso direto a `context.canvas.get` sem validação de tipo.
- Lógica de Gênesis fora do bloco de sessão do banco de dados (risco de desalinhamento).

### O que foi ADICIONADO:
- Chamada assíncrona para `analyze_context(state, original_message)`.
- Extração segura de `tema_txt` e `prob_txt` para o prompt do Gênesis.
- Persistência explícita (`db.add`, `db.commit`, `db.refresh`) da nova Alma no catálogo SQL.
- Log de persistência: `[DEBATE:PERSISTENCE] Nova Alma '...' salva no catálogo`.

---

## 3. Validação Acadêmica (TDD/XP)

- **Script Reprodução (RED)**: `app/tests/reproduce_bug.py` confirmou `ValidationError` (4 erros).
- **Script Verificação (GREEN)**: `app/tests/verify_fix.py` validou sucesso tanto com `BackendState` (TypedDict) quanto com `GraphState` (Pydantic).
- **Refatoração XP**: O teste `verify_fix.py` falhou na primeira run por falta de `user_id` no mock, forçando a inclusão de todos os campos obrigatórios no ambiente de teste.

---
**Status Final:** Operacional.
**Next Frontier:** Migrar `AcademicLevelEnum` para um banco de dados de metadados para evitar discrepâncias como `PHD` vs `DOCTORATE`.
