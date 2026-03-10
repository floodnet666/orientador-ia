# Documentação do Painel de Admin - Orientador.IA

Esta documentação descreve as funcionalidades, o acesso técnico e a infraestrutura do Painel de Administração do Orientador.IA.

## 1. Acesso e Segurança

O acesso ao Painel de Admin é restrito a utilizadores com a flag `is_admin=True` na base de dados PostgreSQL.

- **URL Base da API**: `/api/admin`
- **Frontend**: Disponível na rota `/admin`
- **Tokens**: Utiliza JWT (Bearer Token). Se um utilizador não for admin, a API retornará `403 Forbidden`.

### Como tornar um utilizador Admin
Via consola SQL (Postgres):
```sql
UPDATE users SET is_admin = True WHERE email = 'seu-email@dominio.com';
```

## 2. Funcionalidades de Gestão

### 2.1 Gestão de Utilizadores
- **Listagem**: Visualização de todos os utilizadores registados.
- **Criação**: Adição manual de utilizadores pelo admin.
- **Remoção**: Eliminação de contas.
- **Reset de Password**: Alteração de password individual ou em bloco (via API).

### 2.2 Gestão de Almas (Agentes)
- **CRUD Completo**: Criar, Editar e Apagar Almas do ecossistema.
- **Configuração de Modelo**: O admin pode alterar qual modelo de LLM (ex: `qwen3.5:4b`) cada Alma utiliza individualmente.
- **Edição de Prompt de Sistema**: Alteração do comportamento base do agente.

### 2.3 Histórico e Rollback de Prompts
Todas as alterações no prompt de sistema de uma Alma são historicizadas na tabela `alma_prompt_history`.
- **Registo**: Inclui o prompt anterior, o novo prompt e o motivo da alteração.
- **Rollback**: Capacidade de reverter para qualquer versão anterior com um único clique.

## 3. Observabilidade e Monitorização

O sistema possui um middleware de observabilidade (`app/main.py`) que regista métricas de performance em tempo real na tabela `system_metrics`.

- **Métricas Capturadas**:
    - Tempo de execução de cada pedido (ms).
    - Status codes (200, 4xx, 5xx).
    - Erros do sistema.
- **Identificação de Gargalos**:
    - O painel destaca automaticamente pedidos que demoram mais de **40 segundos** (comum em falhas ou latência excessiva de LLM).
    - Média de tempo de resposta global.

## 4. Informações Técnicas

### Tabelas Relacionadas (PostgreSQL)
- `users`: Armazena a flag `is_admin`.
- `ecosystem_resources`: Tabela mestre das Almas.
- `alma_prompt_history`: Log de auditoria de prompts.
- `system_metrics`: Dados brutos de performance.

### Sincronização com Qdrant
Sempre que uma Alma é criada ou editada via painel admin, o sistema deve (procedimento recomendado) re-indexar a descrição no Qdrant para manter a busca semântica atualizada.

---
*Documentação gerada automaticamente para Orientador.IA MVP.*
