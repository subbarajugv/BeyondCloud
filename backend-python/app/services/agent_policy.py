"""
Agent Policy Schema - Defines acts, tools, and constraints for an agent.
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum

class ExecutionMode(str, Enum):
    SINGLE = "single"          # No loops (Chat/FAQ)
    MULTI_STEP = "multi_step"  # Tool loops (CoT)
    PLANNER = "planner"        # Plan -> Execute -> Synthesize

class SummarizationPolicy(BaseModel):
    strategy: Literal["auto", "aggressive", "lossless"] = "auto"
    trigger_tokens: int = 12000
    preserve_entities: bool = True

class AgentPolicy(BaseModel):
    """
    Configuration for a specific Agent Persona.
    Policies dictate specific behavior and constraints.
    """
    id: str
    name: str
    description: str
    
    # Execution Graph
    execution_mode: ExecutionMode = ExecutionMode.SINGLE
    planning: bool = False
    
    # Permissions
    allowed_tools: List[str] = Field(default_factory=list)
    allowed_models: List[str] = Field(default_factory=list)
    
    # Constraints
    max_steps: int = 10
    require_approval: bool = False
    
    # Context/Engine Config
    summarization: SummarizationPolicy = Field(default_factory=SummarizationPolicy)
    system_prompt: str
    
    # Metadata
    icon: str = "bot"
    color: str = "blue"
