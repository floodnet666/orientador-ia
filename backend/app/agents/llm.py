from langchain_ollama import ChatOllama
from app.config import settings

def get_llm(model: str = None, temperature: float = 0, num_ctx: int = None):
    """
    Fábrica para instanciar o modelo LLM do Ollama compatível com LangChain/LangGraph.
    Configura automaticamente tools e formato baseado nas configurações.
    """
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model or settings.OLLAMA_CHAT_MODEL,
        temperature=temperature,
        num_ctx=num_ctx or settings.OLLAMA_NUM_CTX,
    )

# Instância padrão para uso geral nos nós do Grafo
llm = get_llm()
