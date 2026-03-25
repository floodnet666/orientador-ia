# Orientador.IA - Changelog

Forçando as "Regras YAGNI", "SOLID", e Zero Bloat conforme requisitado pelo Orientador.IA.

## [2026-03-25] - Protocolo de Resiliência de Interface e Otimização de I/O
Implementação de correções críticas para estabilidade do WebSocket, bypass de limites de upload e persistência de consciência de interface nos agentes.

### ADICIONADO:
- **Double-Channel Prompting (Backend)**: Injetada redundância de instruções em `base_alma.py`.
    - As instruções de interface agora residem no parâmetro `system` da API E como a primeira mensagem de sistema no histórico (`messages`).
    - Adicionado **Lembrete de Recência**: Uma diretiva imperativa é injetada imediatamente antes do último turno do utilizador para combater o esquecimento de contexto longo (RLHF).
- **Regex de Extração Tolerante (Backend)**: Em `app/api/chat.py`, a captura de `<canvas_signal>` foi expandida para suportar aspas simples, espaços arbitrários e variação de caracteres, ignorando falhas estritas de sintaxe da LLM.
- **Auto-Redirect 401 (Frontend)**: Em `src/lib/api.ts`, adicionada interceptação de erro de autorização. O sistema agora limpa o `localStorage` e redireciona para `/login` automaticamente em caso de expiração de token.
- **Resizable Split-Pane (Frontend)**: Implementada interface fluida em `page.tsx` que permite ao utilizador ajustar as proporções entre o Chat e o Whiteboard em tempo real.

### REMOVIDO:
- Removida a dependência do proxy Next.js para uploads e WebSocket. O sistema agora utiliza bypass direto para o backend (porta 8000) em ambiente de desenvolvimento e produção controlada, eliminando o gargalo de 10MB do `body-parser` do Next.js.

### CORRIGIDO:
- **WebSocket Handshake Error**: Corrigido `NameError` em `chat.py` onde a variável `t_connect` era referenciada antes da definição. Restaurado o `await websocket.accept()` no ponto de entrada correto do ciclo de vida.
- **StatelessAlma Corruption**: Restaurada a definição da classe `StatelessAlma` em `base_alma.py` que havia sido acidentalmente truncada durante refatoração de prompts.
- **Nginx Upload Limit**: Aumentado `client_max_body_size` para 50M no proxy para suportar datasets científicos pesados.

---
