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

5.  **Cache & State:** `Redis`
    - Gestão de estados de ingestão assíncrona e cache de sessões Mesa-Redonda.

## Deep Search Engine

O Orientador.IA possui o seu próprio motor de pesquisa heurística que contorna as limitações de contexto de base dos LLMs:

-   Busca concorrente assíncrona para não queimar tokens desnecessariamente e não estar limitado aos dados de treino.
-   **RAG Evolution v2.2.0 (Industrial):**
    - **SPLADE Hashing:** Normalização linguística (Unicode/Accents) para precisão em Português.
    - **Background Ingestion:** Processamento assíncrono via Redis (sem bloqueio de UI).
    - **Source Attribution:** Citações automáticas `[Fonte: doc.pdf]` em cada resposta.
    - **Spotlight UI:** Validação de BBox em tempo real para destaque de evidências.
-   Integração real via API REST Direta:
    1.  **OpenAlex**: Pesquisa global de artigos Open Access (>250 Milhões de papers).
    2.  **SciELO**: Busca prioritária em obras de referência Latino-Americanas e da Península Ibérica.
    3.  **ArXiv**: Consulta de *pre-prints* primariamente de Ciências Exatas e Tecnológicas.

## Como Iniciar

Execute o ficheiro `start_orientador.bat` na raiz do projeto. Este script irá:
1. Validar o Docker.
2. Iniciar os serviços (Postgres, Qdrant, Redis, Ollama).
3. Descarregar/Actualizar os modelos necessários.
4. Executar migrações de base de dados e seed de dados.
