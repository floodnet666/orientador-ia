import asyncio
import os
import sys

# In container, /app is CWD and it contains the 'app' package.
# No need to add it to sys.path if running from /app.

from app.agents.almas.base_alma import StatelessAlma
from app.models.agent_config import AgentConfig, AgentTool, LLMParams

async def test_stateless_alma_init():
    config = AgentConfig(
        id="test_id",
        name="Test Alma",
        persona_description="Test Persona",
        system_prompt="Test Prompt",
        epistemological_stance="Test Stance",
        conflict_patterns=[],
        tools=[
            AgentTool(name="openalex_search"),
            AgentTool(name="rag_query"),
            AgentTool(name="canvas_write")
        ],
        llm_params=LLMParams()
    )
    
    # Mock project_id
    project_id = "45d08640-5f18-4a32-a46c-eff4660fb776"
    
    alma = StatelessAlma(config, project_id=project_id)
    
    print(f"Alma Name: {alma.name}")
    print(f"Tools count: {len(alma.tools)}")
    tool_names = [t.name for t in alma.tools]
    print(f"Tools: {tool_names}")
    
    # DeepSearchTool name is "DeepSearch" or what we assigned in StatelessAlma
    # In StatelessAlma it adds DeepSearchTool (base name = 'DeepSearch')
    # and EmpiricalSearchTool (name = 'search_evidence')
    
    assert "DeepSearch" in tool_names or "openalex_search" in tool_names
    assert "update_whiteboard" in tool_names
    assert "add_canvas_node" in tool_names
    assert "search_evidence" in tool_names
    
    print("SUCCESS: StatelessAlma initialized with correct tools!")

if __name__ == "__main__":
    asyncio.run(test_stateless_alma_init())
