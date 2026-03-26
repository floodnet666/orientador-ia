# Descobertas e Reflexões (Findings)

## Teste de LLM Tool Calling (Baseline)
O script de teste `test_llm_tool_calling.py` foi executado contra o Qwen 2.5 7B local com a instrução explícita: "desenha isso no whiteboard".

**Resultado PROMPT ATUAL (Tags XML):**
- O modelo **ignorou completamente** a regra de usar `<canvas_signal field="tema"... />`.
- Respondeu com um pedido de desculpas: *"Embora eu não possa desenhar diretamente, posso descrever para você..."*
- Produziu um output altamente estruturado em **Markdown** (`### Título da Tese:`, `### Parte 1:`).

## Conclusões Comparativas (TDD Multi-Modelo + Native Tool Calling)
A pedido do utilizador, a arquitetura de teste foi reescrita. No teste anterior (viciado), estávamos a instruir o modelo via texto a *"escrever `<tag>` no fluxo de resposta"* (Zero-Shot). No novo teste correto, passámos um schema real JSON à API do Ollama (`tools=[...]`).
Resultados:
1. **Qwen 2.5 (7B)**: Invoca com sucesso o nó `tool_calls` e anula `content` de texto. Ferramenta NATIVA 100% executada.
2. **NVIDIA Nemotron 3 Nano (4B)**: Invoca com sucesso as ferramentas nativamente através do `tool_calls`.
3. **Google Gemma 3 (4B)**: Incompatível com a API de tools da versão local usada (HTTP 400), limitação técnica da subida do modelo.

> **O Veredicto Real**: O utilizador detetou o flaw. A "surdez" não advinha do modelo, mas sim da ausência do uso da Action Engine nativa suportada pelo Ollama. Ao invés de usar Regex (que é robusto mas passivo), a adoção do **Ollama Native Tools API** é a arquiterura definitiva, padronizada com o mercado (OpenAI/Anthropic).

## Decisão Arquitetural Final
- **Extrator Regex (Descartado)**: Era o melhor caminho passivo, contudo desnecessário se pudermos ter chamadas orientadas a schema nativo.
- **Protocolo de Resiliência v11 (Native Tool Calling)**: **O Novo Campeão**. Implementar integração profunda do pipeline de WebSockets do Backend com o emissor `tool_calls` da API Stream do Ollama. Quando a stream recetor apanhar `tool_calls`, aciona dinamicamente a BD Postgres (`_update_canvas`) e imita o comportamento nativo em tempo real.
