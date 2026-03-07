# Orientador.IA

Plataforma de orientação académica multi-agente.

## Pilha Teconológica (LLMs)

A pilha de modelos foi otimizada para eficiência e precisão funcional:

1.  **Almas (Chat):** `qwen3.5:4b`
    - Substitui o `llama3.1:8b`. 
    - Mais leve (~3.4GB) e com melhor seguimento de instruções em Português.
    - O modo *thinking* foi desativado para maximizar a velocidade de streaming.

2.  **Orquestrador & Canvas:** `qwen3.5:4b`
    - Atua como o "Maestro", decidindo qual Alma responde.
    - Otimizado para saídas JSON estruturadas.

3.  **Guardrails:** `qwen3.5:0.8b`
    - Substitui o `mistral:7b`.
    - Modelo ultra-leve (~500MB) para classificação binária rápida de integridade académica.

4.  **Embeddings:** `nomic-embed-text`
    - Mantido para representação vetorial multilingue de 768 dimensões.

## Como Iniciar

Execute o ficheiro `start_orientador.bat` na raiz do projeto. Este script irá:
1. Validar o Docker.
2. Iniciar os serviços (Postgres, Qdrant, Redis, Ollama).
3. Descarregar/Actualizar os modelos necessários.
4. Executar migrações de base de dados e seed de dados.
