"""
Agent Controller - The runtime engine for Agent Policies.
"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from app.services.agent_registry import AgentRegistry
from app.services.agent_policy import AgentPolicy, ExecutionMode
from app.services.provider_service import provider_service
from app.services.agent_tools import AgentTools
from app.services.mcp_service import mcp_service
from app.tracing import create_span
from app.services.agent_compiler import AgentCompiler, EngineConfig
from app.models.agent import Agent, AgentSpec
from app.database import get_session_sync

class AgentController:
    """
    Executes an Agent Policy by driving the Inference Engine.
    """
    
    def __init__(self, agent_id: str, user_id: str, sandbox_path: str):
        self.user_id = user_id
        self.tools = AgentTools(sandbox_path) 
        self.history: List[Dict] = []
        self.compiler = AgentCompiler()
        
        # 1. Try to load from DB
        self.db_agent = self._load_db_agent(agent_id)
        
        if self.db_agent:
            # Compile Custom Agent
            spec_dict = self.db_agent.spec if isinstance(self.db_agent.spec, dict) else self.db_agent.spec.model_dump()
            spec = AgentSpec(**spec_dict)
            self.engine_config = self.compiler.compile(spec)
            self.agent_name = self.db_agent.name
            self.system_prompt = self.compiler.get_system_message(spec)
            self.id = str(self.db_agent.id)
        else:
            # Fallback to Registry (Legacy/Hardcoded)
            policy = AgentRegistry.get(agent_id) or AgentRegistry.get("chat")
            self.engine_config = EngineConfig(
                model=policy.allowed_models[0] if policy.allowed_models else "gpt-4o",
                allowed_tools=policy.allowed_tools,
                execution_mode=policy.execution_mode.value if hasattr(policy.execution_mode, 'value') else policy.execution_mode,
                max_steps=policy.max_steps,
                summarization={"strategy": "none"},
                output_constraints={"format": "markdown", "citations": True}
            )
            self.agent_name = policy.name
            self.system_prompt = policy.system_prompt
            self.id = policy.id

    def _load_db_agent(self, agent_id: str) -> Optional[Agent]:
        """Try to find agent in database"""
        try:
            with get_session_sync() as session:
                from sqlmodel import select
                # Try ID first if numeric
                if agent_id.isdigit():
                    agent = session.get(Agent, int(agent_id))
                    if agent: return agent
                
                # Try Name match
                statement = select(Agent).where(Agent.name == agent_id)
                results = session.exec(statement)
                return results.first()
        except Exception as e:
            print(f"Error loading DB agent: {e}")
            return None

    async def run(self, message: str) -> Dict[str, Any]:
        """
        Run the agent loop based on policy.
        """
        async with create_span("agent_controller.run") as span:
            span.set_attribute("agent_id", self.id)
            span.set_attribute("mode", self.engine_config.execution_mode)
            
            # 1. Initialize Context
            self.history.append({"role": "user", "content": message})
            
            # 2. Resolve Tools
            openai_tools = self._resolve_tools(self.engine_config.allowed_tools)
            
            # 3. Execute Mode
            if self.engine_config.execution_mode == "single":
                return await self._run_single_step(openai_tools)
            else:
                return await self._run_multi_step(openai_tools)

    def _resolve_tools(self, allowed_tool_names: List[str]) -> List[Dict]:
        """Filter MCP tools by allowed list"""
        openai_tools = []
        all_schemas = mcp_service.get_openai_tools()
        
        for tool in all_schemas:
            name = tool["function"]["name"]
            for allowed in allowed_tool_names:
                if allowed in name:
                    openai_tools.append(tool)
                    break
        return openai_tools

    async def _run_single_step(self, tools: List[Dict]) -> Dict:
        """Execute single inference step"""
        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        
        response = await provider_service.chat_completion(
            messages=messages,
            model=self.engine_config.model,
            tools=tools if tools else None
        )
        
        return {
            "content": response.get("content"),
            "agent": self.agent_name
        }

    async def _run_multi_step(self, tools: List[Dict]) -> Dict:
        """Execute ReAct-style loop"""
        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        steps = 0
        
        while steps < self.engine_config.max_steps:
            steps += 1
            
            # 1. Inference
            response = await provider_service.chat_completion(
                messages=messages,
                model=self.engine_config.model,
                tools=tools
            )
            
            content = response.get("content")
            tool_calls = response.get("tool_calls", [])
            
            # Add assistant message
            msg = {"role": "assistant"}
            if content: msg["content"] = content
            if tool_calls: msg["tool_calls"] = tool_calls
            messages.append(msg)
            
            # 2. If no tool calls, we are done
            if not tool_calls:
                return {"content": content, "agent": self.agent_name, "steps": steps}
                
            # 3. Execute Tools
            for call in tool_calls:
                func_name = call["function"]["name"]
                args_str = call["function"]["arguments"]
                call_id = call["id"]
                
                # ENFORCEMENT: Check if tool is allowed
                is_allowed = any(allowed in func_name for allowed in self.engine_config.allowed_tools)
                if not is_allowed:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": f"Error: Tool '{func_name}' is not allowed for this agent."
                    })
                    continue

                try:
                    args = json.loads(args_str)
                    result_dict = await mcp_service.call_tool_by_openai_name(func_name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(result_dict)
                    })
                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": f"Error: {str(e)}"
                    })
        
        return {"content": "Max steps reached.", "agent": self.agent_name, "steps": steps}
