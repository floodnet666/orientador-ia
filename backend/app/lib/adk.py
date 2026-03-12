import time
import json
import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, AsyncIterator
import logging
from pydantic import BaseModel
from app.services.ollama_client import OllamaClient

T = TypeVar("T", bound=BaseModel)

class Tool:
    """Shim for adk.Tool"""
    def __init__(self, name: str, func: callable, description: str):
        self.name = name
        self.func = func
        self.description = description

class Agent(Generic[T]):
    """Shim for adk.Agent"""
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        tools: List[Tool] = None,
        output_schema: Optional[Type[T]] = None
    ):
        self.name = name
        # model format 'ollama/llama3.1:8b' -> 'llama3.1:8b'
        self.model_name = model.replace("ollama/", "")
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.output_schema = output_schema
        self.client = OllamaClient()

    def _format_tools(self) -> List[Dict[str, Any]]:
        """Converts adk.Tool to Ollama Tool Schema."""
        if not self.tools:
            return None
            
        formatted_tools = []
        for tool in self.tools:
            # Basic schema derivation: assume one string argument 'query' for simplicity in MVP
            # A robust implementation would use inspect.signature(tool.func)
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        return formatted_tools

    async def stream(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        """Async generator that yields content chunks, handling tools internally."""
        full_context = f"Context: {json.dumps(context)}\n\nUser Message: {input_text}" if context else input_text
        
        messages = [{"role": "user", "content": full_context}]
        tools_schema = self._format_tools()
        options = {"num_ctx": settings.OLLAMA_NUM_CTX}
        
        for _ in range(3):
            tool_calls = None
            async for chunk in self.client.chat_stream(
                model=self.model_name, 
                messages=messages, 
                system=self.system_prompt,
                tools=tools_schema,
                options=options
            ):
                if chunk.startswith('{"tool_calls":'):
                    tool_calls = json.loads(chunk)["tool_calls"]
                    break
                yield chunk

            if tool_calls:
                messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    func_args = tc["function"]["arguments"]
                    tool = next((t for t in self.tools if t.name == func_name), None)
                    if tool:
                        try:
                            if asyncio.iscoroutinefunction(tool.func):
                                result = await tool.func(**func_args)
                            else:
                                result = tool.func(**func_args)
                            messages.append({"role": "tool", "content": json.dumps(result), "name": func_name})
                        except Exception as e:
                            messages.append({"role": "tool", "content": json.dumps({"error": str(e)}), "name": func_name})
                    else:
                        messages.append({"role": "tool", "content": json.dumps({"error": "Tool not found"}), "name": func_name})
            else:
                break

    async def run(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Union[T, str]:
        """Simulates agent execution using OllamaClient with tool support"""
        full_context = f"Context: {json.dumps(context)}\n\nUser Message: {input_text}" if context else input_text
        
        messages = [{"role": "user", "content": full_context}]
        tools_schema = self._format_tools()
        options = {"num_ctx": settings.OLLAMA_NUM_CTX}
        
        # Tool execution loop (max 3 iterations to prevent infinite loops)
        for _ in range(3):
            response_content = ""
            tool_calls = None
            
            async for chunk in self.client.chat_stream(
                model=self.model_name, 
                messages=messages, 
                system=self.system_prompt,
                tools=tools_schema,
                options=options
            ):
                if chunk.startswith('{"tool_calls":'):
                    # Intercept tool calls
                    tool_calls = json.loads(chunk)["tool_calls"]
                    break
                response_content += chunk

            if tool_calls:
                # Add assistant's tool call message
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls
                })
                
                # Execute tools
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    func_args = tc["function"]["arguments"]
                    
                    tool = next((t for t in self.tools if t.name == func_name), None)
                    if tool:
                        try:
                            # Await if async, else call directly
                            if asyncio.iscoroutinefunction(tool.func):
                                result = await tool.func(**func_args)
                            else:
                                result = tool.func(**func_args)
                                
                            messages.append({
                                "role": "tool",
                                "content": json.dumps(result),
                                "name": func_name
                            })
                        except Exception as e:
                            messages.append({
                                "role": "tool",
                                "content": json.dumps({"error": str(e)}),
                                "name": func_name
                            })
                    else:
                        messages.append({
                            "role": "tool",
                            "content": json.dumps({"error": "Tool not found"}),
                            "name": func_name
                        })
                # Loop continues to send tool results back to the model
            else:
                # No more tool calls, construct final response
                break

        if self.output_schema:
            import re
            try:
                # Attempt to extract JSON if schema is required
                cleaned_response = response_content.strip()
                
                # Robust extraction: find the first { and last }
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(0)
                elif "```json" in cleaned_response:
                    cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned_response:
                    cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()
                
                return self.output_schema.model_validate_json(cleaned_response)
            except Exception as e:
                print(f"ADK Shim Validation Error for agent {self.name}: {e}")
                # Fallback: if we can't parse, return raw to avoid total failure
                return response_content
        
        return response_content

class Runner:
    """Shim for adk.Runner"""
    @staticmethod
    async def run_sequence(agents: List[Agent], input_text: str, initial_context: Optional[Dict[str, Any]] = None) -> List[Any]:
        results = []
        current_context = initial_context or {}
        current_input = input_text
        
        for agent in agents:
            result = await agent.run(current_input, current_context)
            results.append(result)
            # Simple context propagation logic
            if isinstance(result, BaseModel):
                current_context.update(result.model_dump())
            elif isinstance(result, str):
                current_context[f"{agent.name}_output"] = result
        
        return results
