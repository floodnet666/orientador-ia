# Documentação de Integridade de Ciclo de Vida: Deleção de Almas (v1)

> **Data:** 2026-03-30
> **Status:** Implementado e Verificado
> **Escopo:** Backend (SQLModels, Alembic, Admin API)

## 1. Problema Identificado
A deleção de "Almas" (EcosystemResource) no painel administrativo estava falhando com erro `500 Internal Server Error` (PostgreSQL `ForeignKeyViolationError`). Isso ocorria porque sub-recursos e referências em outras tabelas não possuíam regras de remoção automáticas, bloqueando a deleção da entidade primária.

## 2. Alterações Realizadas

### 2.1 Modelos SQL (`backend/app/models/sql_models.py`)

#### `EcosystemResource` (Alma)
- **Adicionado:** Relação explícita com o histórico de prompts.
- **Lógica:** `prompt_history = relationship("AlmaPromptHistory", back_populates="alma", cascade="all, delete-orphan")`.
- **Racional:** Garante que ao deletar uma Alma, todos os registros de histórico vinculados sejam removidos via SQLAlchemy (emulando ou complementando o CASCADE do banco).

#### `Project`
- **Modificado:** Constraints `theoretical_alma_id` e `methodological_alma_id`.
- **Lógica:** Adicionado `ondelete="SET NULL"` em ambas as chaves estrangeiras.
- **Racional:** Projetos acadêmicos são entidades perenes. Se uma Alma (especialista) for removida do ecossistema, o projeto deve persistir, apenas perdendo a referência para aquela Alma específica (campo torna-se `NULL`).

#### `ChatMessage`
- **Modificado:** Constraint `alma_id`.
- **Lógica:** Adicionado `ondelete="SET NULL"`.
- **Racional:** Histórico de chat deve ser preservado para integridade da conversa do usuário, mesmo que a Alma que gerou a resposta não exista mais no sistema.

### 2.2 API Admin (`backend/app/api/admin.py`)
- **Limpeza:** Removida a lógica de "limpeza manual" (comentários que sugeriam deletar dependências antes da alma).
- **Simplificação:** A rota `delete_alma` agora realiza apenas o `db.delete(alma)`, confiando plenamente na integridade referencial do banco de dados e do ORM.

### 2.3 Migrações (Alembic `f71df0d27060`)
- **Ação:** Criação de migração manual para aplicar as constraints em nível de banco (PostgreSQL).
- **Detalhe do `upgrade()`:**
    1. Drop de constraints antigas (`IF EXISTS`) para garantir idempotência.
    2. Criação de `fk_alma_prompt_history_alma` com `ON DELETE CASCADE`.
    3. Criação de `fk_projects_theoretical_alma` e `fk_projects_methodological_alma` com `ON DELETE SET NULL`.
    4. Criação de `fk_chat_messages_alma` com `ON DELETE SET NULL`.

## 3. Protocolo de Verificação (Zero Bloat Verify)
A verificação foi realizada através do script `scripts/verify_alma_delete_fix.py`, cobrindo:
1. **Criação:** Alma -> Histórico -> Projeto Associado.
2. **Execução:** Deleção da Alma via Session.
3. **Asserção CASCADE:** Confirmação de que `AlmaPromptHistory` foi removido.
4. **Asserção SET NULL:** Confirmação (via nova sessão de DB para evitar cache de identity map) de que o `Project` persiste e seu campo `theoretical_alma_id` é `None`.

## 4. Próxima Fronteira de Investigação
- **Cleanup de Arquivos:** Investigar se a deleção de Almas que possuem arquivos físicos (avatares customizados) requer um hook adicional para limpeza de storage (S3/Local).
- **Impacto no Debate:** Validar se logs de debate (v8) lidam graciosamente com Almas setadas como `NULL` na visualização histórica.
