from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel, Relationship

class AgentSpec(SQLModel):
    """
    Serializable execution policy for a custom agent.
    This defines 'what' the agent can do and 'how' it should behave.
    """
    objective: str = Field(description="The primary goal or persona description")
    allowed_models: List[str] = Field(default=["gpt-4o", "gemini-1.5-pro"])
    allowed_tools: List[str] = Field(default=["rag", "web_search"])
    execution_mode: str = Field(default="planner", description="single, multi-step, or planner")
    max_steps: int = Field(default=5)
    summarization: Dict[str, Any] = Field(default={"strategy": "none"})
    output_constraints: Dict[str, Any] = Field(default={"format": "markdown", "citations": True})

class AgentBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    
class Agent(AgentBase, table=True):
    """
    Database record for a Custom Agent.
    """
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Store the spec as a JSON object
    spec: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Optional: Link to a user
    user_id: Optional[str] = Field(default="default", index=True)

class AgentCreate(AgentBase):
    spec: AgentSpec

class AgentRead(AgentBase):
    id: int
    created_at: datetime
    spec: AgentSpec

class AgentUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    spec: Optional[AgentSpec] = None
