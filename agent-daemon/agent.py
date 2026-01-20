"""
BeyondCloud Agent - Core Agent Class

An agent that:
- Connects to an LLM (local llama.cpp or provider)
- Discovers tools from MCP servers
- Runs an agentic loop: Goal → Plan → Execute → Check → Repeat
"""

import httpx
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger("agent")


# ========== Models ==========

class ToolSchema(BaseModel):
    """Tool schema from MCP server"""
    name: str
    description: str
    inputSchema: Dict[str, Any] = {}


class ToolCall(BaseModel):
    """Tool call from LLM"""
    id: str
    name: str
    arguments: Dict[str, Any]


class AgentMessage(BaseModel):
    """Message in agent conversation"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


@dataclass
class AgentConfig:
    """Agent configuration"""
    llm_url: str = "http://localhost:8080/v1"  # llama.cpp server
    mcp_urls: List[str] = field(default_factory=lambda: ["http://localhost:8001/api/mcp"])
    max_steps: int = 10
    timeout: int = 120
    system_prompt: str = "You are a helpful AI assistant with access to tools. Use them to help the user."


# ========== Agent Class ==========

class Agent:
    """
    A proper agent with:
    - LLM client for reasoning
    - Tool discovery from MCP servers
    - Agentic loop for goal completion
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.tools: List[ToolSchema] = []
        self.tool_sources: Dict[str, str] = {}  # tool_name -> mcp_url
        self.messages: List[AgentMessage] = []
        self.http = httpx.AsyncClient(timeout=self.config.timeout)

    async def discover_tools(self, mcp_urls: Optional[List[str]] = None) -> List[ToolSchema]:
        """Discover tools from MCP servers"""
        urls = mcp_urls or self.config.mcp_urls
        self.tools = []
        self.tool_sources = {}

        for url in urls:
            try:
                response = await self.http.get(f"{url}/tools")
                if response.status_code == 200:
                    data = response.json()
                    for tool_data in data.get("tools", []):
                        tool = ToolSchema(**tool_data)
                        self.tools.append(tool)
                        self.tool_sources[tool.name] = url
                    logger.info(f"Discovered {len(data.get('tools', []))} tools from {url}")
            except Exception as e:
                logger.warning(f"Failed to discover tools from {url}: {e}")

        return self.tools

    async def run(self, goal: str) -> str:
        """
        Execute the agentic loop.
        
        Args:
            goal: The user's goal/task
            
        Returns:
            Final response from the agent
        """
        # Initialize conversation
        self.messages = [
            AgentMessage(role="system", content=self.config.system_prompt),
            AgentMessage(role="user", content=goal)
        ]

        # Ensure tools are discovered
        if not self.tools:
            await self.discover_tools()

        # Agentic loop
        for step in range(self.config.max_steps):
            logger.info(f"Agent step {step + 1}/{self.config.max_steps}")

            # Call LLM
            response = await self._call_llm()

            if response is None:
                return "Error: LLM call failed"

            # Check for tool calls
            if response.tool_calls:
                # Execute tools
                tool_results = await self._execute_tools(response.tool_calls)
                
                # Add tool results to conversation
                for result in tool_results:
                    self.messages.append(result)
                
                # Continue loop
                continue

            # No tool calls = final response
            return response.content

        return "Maximum steps reached without completion"

    async def _call_llm(self) -> Optional[AgentMessage]:
        """Call the LLM with current messages and tools"""
        try:
            # Convert tools to OpenAI format
            tools_openai = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                }
                for t in self.tools
            ]

            # Build request
            payload = {
                "model": "local",
                "messages": [
                    {"role": m.role, "content": m.content}
                    for m in self.messages
                ],
                "tools": tools_openai if tools_openai else None,
                "tool_choice": "auto" if tools_openai else None
            }

            response = await self.http.post(
                f"{self.config.llm_url}/chat/completions",
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"LLM error: {response.text}")
                return None

            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            # Parse tool calls if present
            tool_calls = None
            if message.get("tool_calls"):
                tool_calls = []
                for tc in message["tool_calls"]:
                    import json
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc["function"]["name"],
                        arguments=json.loads(tc["function"].get("arguments", "{}"))
                    ))

            assistant_msg = AgentMessage(
                role="assistant",
                content=message.get("content", ""),
                tool_calls=tool_calls
            )
            self.messages.append(assistant_msg)

            return assistant_msg

        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return None

    async def _execute_tools(self, tool_calls: List[ToolCall]) -> List[AgentMessage]:
        """Execute tool calls on their respective MCP servers"""
        results = []

        for tc in tool_calls:
            mcp_url = self.tool_sources.get(tc.name)
            if not mcp_url:
                result = f"Error: Tool '{tc.name}' not found"
            else:
                result = await self._execute_single_tool(mcp_url, tc.name, tc.arguments)

            results.append(AgentMessage(
                role="tool",
                content=result,
                tool_call_id=tc.id
            ))

        return results

    async def _execute_single_tool(self, mcp_url: str, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a single tool on an MCP server"""
        try:
            response = await self.http.post(
                f"{mcp_url}/tools/call",
                json={"name": name, "arguments": arguments}
            )

            if response.status_code != 200:
                return f"Error: {response.text}"

            data = response.json()
            content = data.get("content", [])
            
            # Extract text from content
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) or str(data)

        except Exception as e:
            return f"Error executing tool: {e}"

    async def close(self):
        """Cleanup resources"""
        await self.http.aclose()
