# GUIA_MANUTENCAO.md - Orientador.IA

> [!IMPORTANT]
> Documento de alta densidade para manutenção do sistema. Ignorar seções não relacionadas à tarefa atual.

## 1. Stack Tecnológica & Dependências

### 1.1 Backend (Python 3.12 - uv)
| Lib | Versão | Ponto de Atenção |
| :--- | :--- | :--- |
| `fastapi` | `^0.115.8` | ASGI standard. Use `uv run`. |
| `pydantic` | `^2.10.6` | **V2 required**. Use `model_dump()`, não `dict()`. |
| `sqlalchemy` | `^2.0.38` | Estilo declarativo 2.0. |
| `qdrant-client` | `==1.12.0` | Pinada para compatibilidade com v1.12.1 do server. |
| `pydantic-settings` | `^2.7.1` | Gestão de `.env`. |
| `uvicorn` | `^0.34.0` | Entry point para o servidor. |

### 1.2 Frontend (Next.js 16 / React 19)
| Lib | Versão | Ponto de Atenção |
| :--- | :--- | :--- |
| `next` | `16.1.6` | App Router mandatory. |
| `react` | `19.2.3` | **React 19 hooks**. Cuidado com hydration errors. |
| `tldraw` | `^4.5.3` | **CRÍTICO: Use `richText: toRichText(s)` para labels. Prop `text` inválida.** |
| `tailwindcss` | `^4` | v4 engine (CSS-first). |
| `zustand` | `^5.0.11` | Shared state via Store. |

---

## 2. Pontos de Atenção (Anti-Erro para Agentes)

### 2.1 tldraw Drawing Pattern (v4.5.3+)
Agentes costumam assumir `props: { text: "..." }`. Em v4.5.3, isso causa `ValidationError`.
```tsx
// INCORRETO
props: { text: action.label }

// CORRETO
import { toRichText } from 'tldraw';
// ...
props: { richText: toRichText(action.label), textAlign: 'middle' }
```

### 2.2 Networking & Proxy Bypass
O sistema possui gárgalos de proxy no Next.js Dev Server (limite 10MB e instabilidade de WS).
- **Uploads > 10MB**: Devem ser enviados diretamente para `PORT 8000` (Backend).
- **WebSockets**: Conexão direta via `ws://localhost:8000/ws`.
- **Ollama Host**: Se dockerizado, use `host.docker.internal:11434`. Se local, `localhost:11434`.

### 2.3 ADK Regex Implementation
O `adk.py` utiliza Regex para extrair JSON de modelos LLM instáveis.
- **Formato**: Sempre envolva o retorno das ferramentas em blocos JSON válidos.
- **Fail-safe**: O backend remove preâmbulos e posfácios automáticos.

---

## 3. Topologia de Fluxo (Soul-Canvas Bridge)

```mermaid
graph LR
    Alma[BaseAlma.py] -- "tool_call" --> ADK[adk.py]
    ADK -- "ActionToken (JSON)" --> WS[WebSocket Bridge]
    WS -- "type: action" --> FE[WhiteboardCanvas.tsx]
    FE -- "toRichText()" --> Tldraw[tldraw Editor]
    Tldraw -- "getSnapshot() (Auto-save)" --> BE[SQLite:canvas_json]
```

### 3.1 Whiteboard Persistence (Snapshot)
A persistência do Whiteboard não é baseada em nós individuais no SQLite, mas em um **Snapshot integral** do Tldraw.
- **Auto-save**: Ocorre no `frontend/src/components/whiteboard/WhiteboardCanvas.tsx` via `editor.store.listen`.
- **Debounce**: 3 segundos para evitar sobrecarga de rede.
- **Trigger**: Movimentações manuais do usuário.
- **IA Sync**: Ações da IA (`add_canvas_node`) aparecem via WebSocket, mas o auto-save subsequente do frontend garante que o novo nó entre no snapshot persistente.

---

## 4. Comandos Rápidos de Manutenção
- **Backend Clean Run**: `uv run uvicorn app.main:app --reload`
- **Frontend Dev**: `npm run dev`
- **Full E2E Test**: `uv run backend/tests/test_e2e_whiteboard.py`
- **Reinstall All**: `docker-compose down -v && start_orientador.bat`

---

## 5. Histórico de Correções Críticas (Contexto para Agentes)

### 5.1 NameError: ORCHESTRATOR_SYSTEM_PROMPT (Março 2026)
- **Causa**: Variável utilizada no construtor do `adk.Agent` antes de ser definida geograficamente no arquivo.
- **Solução**: Mover a string de prompt para o topo do arquivo, antes da inicialização do agente.

### 5.2 ImportError: search_almas & Payload Key Mismatch
- **Causa**: Função `search_almas` referenciada no `match_engine.py` mas não implementada no `qdrant_service.py`. Adicionalmente, havia uma inconsistência entre as chaves `type` e `alma_type` no payload do Qdrant.
- **Solução**: Implementação da função `search_almas` e padronização da chave para `alma_type` em todo o ciclo de vida do vetor (indexação e busca).

---
*Protocolo DocumentationSphinx - Integridade Zero Bloat*
