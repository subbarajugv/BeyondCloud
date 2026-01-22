"""
Agent Registry - The catalog of available agents and their policies.
"""
from typing import Dict, List, Optional
from app.services.agent_policy import AgentPolicy, ExecutionMode

class AgentRegistry:
    """
    Static registry of agent policies. 
    In the future, this could load from DB or YAML files.
    """
    
    _agents: Dict[str, AgentPolicy] = {}
    
    @classmethod
    def initialize_defaults(cls):
        """Register default agents"""
        
        # 1. Standard Chat Agent
        cls.register(AgentPolicy(
            id="chat",
            name="Chat Assistant",
            description="A helpful AI assistant for general conversation.",
            execution_mode="single",
            planning=False,
            allowed_tools=["rag_retrieve", "calculator"],
            allowed_models=["ollama", "openai", "groq"],
            system_prompt="You are a helpful AI assistant.",
            max_steps=1,
            icon="message-square",
            color="blue"
        ))
        
        # 2. Research Agent
        cls.register(AgentPolicy(
            id="research",
            name="Deep Researcher",
            description="Performs multi-step research using web search.",
            execution_mode="planner",
            planning=True,
            allowed_tools=["rag_retrieve", "search_web", "read_url"],
            allowed_models=["openai", "gemini"],
            summarization={"strategy": "aggressive"},
            system_prompt="You are a Deep Researcher. Create a research plan, execute it, and synthesize findings.",
            max_steps=10,
            icon="globe",
            color="purple"
        ))
        
        # 3. Analyst Agent
        cls.register(AgentPolicy(
            id="analyst",
            name="Data Analyst",
            description="Analyzes data and code.",
            execution_mode="multi_step",
            planning=True,
            allowed_tools=["python_repl", "list_dir", "read_file"],
            allowed_models=["gpt-4-turbo", "claude-3-opus"],
            summarization={"strategy": "lossless"},
            system_prompt="You are a Data Analyst. Use Python to analyze data and define insights.",
            max_steps=15,
            icon="bar-chart",
            color="orange"
        ))
        
    @classmethod
    def register(cls, policy: AgentPolicy):
        cls._agents[policy.id] = policy
        
    @classmethod
    def get(cls, agent_id: str) -> Optional[AgentPolicy]:
        if not cls._agents:
            cls.initialize_defaults()
        return cls._agents.get(agent_id)
        
    @classmethod
    def list_all(cls) -> List[AgentPolicy]:
        if not cls._agents:
            cls.initialize_defaults()
        return list(cls._agents.values())

# Initialize on import? Or lazy load
agent_registry = AgentRegistry
