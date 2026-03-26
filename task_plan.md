# Plano de Teste e Evolução do Whiteboard (Canvas)

## Fases do Projeto

### Fase 1: Testes de Isolamento e Baseline (TDD)
- status: complete
- Resultado: O Qwen2.5-7B local demonstrou "surdez técnica" às tags XML (`<canvas_signal>`). Ignora os comandos rígidos e opta por estruturar a resposta em Markdown natural (`### Título`, `**Tema:**`). A tentativa de Forçar JSON Array (OpenMAIC mode) via prompt também falhou sem uso de restrições de schema (format="json").

### Fase 2: Reflexão e Decisão de Arquitetura
- status: complete
- Competição de Abordagens:
  1. **Criar uma Skill TDD**: Adicionaria Overhead de contexto. O modelo continuaria a preferir texto livre se não houvesse constrições físicas no endpoint.
  2. **OpenMAIC (JSON puro)**: Exigiria forçar `format="json"` na API do Ollama e reescrever o parser inteiro do backend e frontend para suportar um array JSON em tempo real. É poderoso, mas muito intrusivo para a stack atual.
  3. **Extrator Regex (v11)**: A solução de menor resistência. O modelo GERA Markdown perfeitamente de forma orgânica. Se o backend simplesmente escutar este Markdown via Expressões Regulares (`re.search(r'### Tema: (.+)')`), o Canvas é atualizado *magicamente* sem o Agente ter de "aprender" a programar ferramentas.

### Escalonamento (Apresentação ao Utilizador)
- Apresentar a descoberta sobre o Qwen2.5-7B e recomendar o caminho menos disruptivo (v11 Regex), que cumpre o objetivo de não "mudar agressivamente" a stack.
