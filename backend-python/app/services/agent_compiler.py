from typing import Dict, Any, List
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Agent specification for compilation."""
    allowed_models: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    execution_mode: str = "single"
    max_steps: int = 10
    summarization: Dict[str, Any] = Field(default_factory=dict)
    output_constraints: Dict[str, Any] = Field(default_factory=dict)
    objective: str = "a helpful AI assistant"

class EngineConfig:
    """
    The unified configuration format that the inference engine consumes.
    """
    def __init__(
        self,
        model: str,
        allowed_tools: List[str],
        execution_mode: str,
        max_steps: int,
        summarization: Dict[str, Any],
        output_constraints: Dict[str, Any]
    ):
        self.model = model
        self.allowed_tools = allowed_tools
        self.execution_mode = execution_mode
        self.max_steps = max_steps
        self.summarization = summarization
        self.output_constraints = output_constraints

class AgentCompiler:
    """
    Compiles a high-level AgentSpec into a runtime EngineConfig.
    """
    
    def compile(self, spec: AgentSpec, override_model: str = None) -> EngineConfig:
        # Determine the model: use override if provided, else the first allowed model
        final_model = override_model if override_model in spec.allowed_models else spec.allowed_models[0]
        
        # In a real system, 'compilation' might involve:
        # 1. Resolving tool definitions from a registry
        # 2. Injecting system prompts based on the objective
        # 3. Setting hyper-parameters based on task type
        
        return EngineConfig(
            model=final_model,
            allowed_tools=spec.allowed_tools,
            execution_mode=spec.execution_mode,
            max_steps=spec.max_steps,
            summarization=spec.summarization,
            output_constraints=spec.output_constraints
        )

    def get_system_message(self, spec: AgentSpec) -> str:
        """
        Translates the agent objective and output constraints into a system prompt.
        """
        prompt = [
            f"You are {spec.objective}.",
            f"Your execution strategy is: {spec.execution_mode}.",
            f"You have access to the following tools: {', '.join(spec.allowed_tools)}.",
            f"Output format: {spec.output_constraints.get('format', 'markdown')}."
        ]
        
        if spec.output_constraints.get('citations'):
            prompt.append("You MUST provide citations for all facts.")
            
        return " ".join(prompt)
