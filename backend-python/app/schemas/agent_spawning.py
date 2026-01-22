"""
Agent Spawning Schemas - Pydantic models for agent templates, instances, and events.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


# ============================================================
# POLICY COMPONENTS
# ============================================================

class SummarizationPolicy(BaseModel):
    """Defines how context summarization should be handled."""
    strategy: Literal["none", "hierarchical", "lossless"] = "none"
    compression_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)


class AgentSpec(BaseModel):
    """
    The policy specification for an agent template.
    These define upper bounds - actual permissions are computed at runtime.
    """
    allowed_models: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    execution_mode: Literal["single", "multi-step", "planner"] = "single"
    max_steps: int = Field(default=5, gt=0, le=20)
    summarization: SummarizationPolicy = Field(default_factory=SummarizationPolicy)
    output_format: Literal["text", "markdown", "json"] = "markdown"
    system_prompt: Optional[str] = None


# ============================================================
# TEMPLATE SCHEMAS
# ============================================================

class AgentTemplateCreate(BaseModel):
    """Request schema for creating a new agent template."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    spec: AgentSpec
    scope: Literal["personal", "org", "global"] = "personal"
    required_roles: List[str] = Field(default_factory=list)
    icon: Optional[str] = None
    color: Optional[str] = None


class AgentTemplateUpdate(BaseModel):
    """Request schema for updating an agent template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    spec: Optional[AgentSpec] = None
    scope: Optional[Literal["personal", "org", "global"]] = None
    required_roles: Optional[List[str]] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class AgentTemplateResponse(BaseModel):
    """Response schema for agent template."""
    id: UUID
    name: str
    description: Optional[str]
    owner_id: UUID
    org_id: Optional[UUID]
    scope: str
    spec: AgentSpec
    version: int
    required_roles: List[str]
    icon: Optional[str]
    color: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# INSTANCE SCHEMAS
# ============================================================

class SpawnRequest(BaseModel):
    """Request schema for spawning an agent instance."""
    template_id: UUID
    task: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class SpawnIntentRequest(BaseModel):
    """Request from an agent to spawn a child agent."""
    template_name: str
    task: str
    context: Optional[Dict[str, Any]] = None


class InstanceStatusResponse(BaseModel):
    """Response schema for agent instance status."""
    id: UUID
    template_id: Optional[UUID]
    template_version: Optional[int]
    spawned_by_user_id: UUID
    parent_instance_id: Optional[UUID]
    root_instance_id: Optional[UUID]
    depth: int
    status: str
    current_state: str
    step: int
    task: Optional[str]
    tokens_used: int
    cost_usd: float
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstanceResultResponse(BaseModel):
    """Response with full instance details including result."""
    id: UUID
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    tokens_used: int
    steps: int


# ============================================================
# EVENT SCHEMAS
# ============================================================

class AgentEventCreate(BaseModel):
    """Internal schema for creating agent events."""
    instance_id: UUID
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    tokens_used: int = 0
    latency_ms: Optional[int] = None


class AgentEventResponse(BaseModel):
    """Response schema for agent events."""
    id: UUID
    instance_id: UUID
    event_type: str
    payload: Dict[str, Any]
    trace_id: Optional[str]
    span_id: Optional[str]
    tokens_used: int
    latency_ms: Optional[int]
    timestamp: datetime

    class Config:
        from_attributes = True


# ============================================================
# SPAWN GOVERNANCE
# ============================================================

class SpawnPolicy(BaseModel):
    """Configuration for spawn limits and governance."""
    max_depth: int = 3
    max_total_instances: int = 50
    max_children_per_agent: int = 10
    inherit_parent_budget: bool = True
    allowed_child_templates: Optional[List[str]] = None


class EffectivePermissions(BaseModel):
    """Computed permissions after intersection resolution."""
    tools: List[str]
    models: List[str]
    max_steps: int
    token_budget: int
