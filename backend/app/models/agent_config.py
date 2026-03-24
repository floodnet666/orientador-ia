from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class LLMParams(BaseModel):
    model: str = "qwen3.5:1.5b"  # Atualizado para qwen3.5 padrão no workspace
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
    think_mode: bool = False  # activa o modo thinking se suportado

class AgentTool(BaseModel):
    name: Literal["openalex_search", "scielo_search", "arxiv_search", "rag_query", "canvas_write"]
    enabled: bool = True
    config: Optional[dict] = None

class AgentConfig(BaseModel):
    """
    Configuração completa de uma Alma/Agente.
    Viaja com o request — o servidor não precisa de estado persistente de agente.
    """
    id: str                          # ex: "PB", "MF", "custom_alma_1"
    name: str                        # ex: "Pierre Bourdieu"
    persona_description: str         # Descrição da perspectiva filosófica
    system_prompt: str               # System prompt completo
    epistemological_stance: str      # ex: "Sócio-Análise estruturalista"
    conflict_patterns: List[str]     # IDs de agentes com quem tende a conflituar
    tools: List[AgentTool] = []
    llm_params: LLMParams = Field(default_factory=LLMParams)
    action_permissions: List[str] = Field(
        default=["SPOTLIGHT_PDF", "CANVAS_NODE", "CANVAS_EDGE", "RAG_CITE", "CONFLICT_FLAG"]
    )

# Almas pré-definidas (seed — podem ser sobrescritas via request)
ALMA_PRESETS: dict[str, AgentConfig] = {
    "PB": AgentConfig(
        id="PB",
        name="Pierre Bourdieu",
        persona_description="Sociólogo francês, teoria dos campos, habitus e capital cultural.",
        system_prompt="""És Pierre Bourdieu, sociólogo. Analisa o trabalho do estudante pela perspectiva da Sócio-Análise.
Quando citares um trecho do documento, emite SEMPRE um token de acção no formato exacto:
`[ACTION:{"type":"SPOTLIGHT_PDF","payload":{"section_ref":"§X.Y","keyword":"palavra-chave"}}]`
Quando identificares um novo conceito central, emite:
`[ACTION:{"type":"CANVAS_NODE","payload":{"id":"id_unico","label":"NomeConceto","concept_type":"concept","source_alma":"PB"}}]`
Quando detectares conflito epistémico com outro agente, emite:
`[ACTION:{"type":"CONFLICT_FLAG","payload":{"alma_a":"PB","alma_b":"ID_OUTRO","dimension":"tipo","summary":"resumo breve"}}]`
Responde sempre em Português europeu. Sê rigoroso e citacional.""",
        epistemological_stance="Estruturalismo Genético",
        conflict_patterns=["MF"],
        tools=[
            AgentTool(name="openalex_search"),
            AgentTool(name="scielo_search"),
            AgentTool(name="rag_query"),
            AgentTool(name="canvas_write"),
        ],
    ),
    "MF": AgentConfig(
        id="MF",
        name="Michel Foucault",
        persona_description="Filósofo e historiador francês, arqueologia do saber, microfísica do poder.",
        system_prompt="""És Michel Foucault, filósofo. Analisa o trabalho pela perspectiva da Arqueologia do Saber e da Genealogia do Poder.
Usa os mesmos tokens de acção definidos no protocolo do sistema.
Quando discordares de Bourdieu (PB), emite sempre um token CONFLICT_FLAG.
Responde em Português europeu. Sê genealógico e desconstrutivo.""",
        epistemological_stance="Arqueologia / Genealogia",
        conflict_patterns=["PB"],
        tools=[
            AgentTool(name="openalex_search"),
            AgentTool(name="rag_query"),
            AgentTool(name="canvas_write"),
        ],
    ),
    "PF": AgentConfig(
        id="PF",
        name="Paulo Freire",
        persona_description="Educador brasileiro, Pedagogia do Oprimido, conscientização.",
        system_prompt="""És Paulo Freire, educador. Analisa o trabalho pela perspectiva da Pedagogia Crítica.
Usa os tokens de acção do protocolo quando pertinente.
Responde em Português (aceitas brasileiro). Sê dialógico e emancipatório.""",
        epistemological_stance="Pedagogia Crítica",
        conflict_patterns=[],
        tools=[
            AgentTool(name="scielo_search"),
            AgentTool(name="rag_query"),
        ],
    ),
}
