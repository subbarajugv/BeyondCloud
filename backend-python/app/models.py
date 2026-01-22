"""
SQLAlchemy ORM Models for BeyondCloud Python Backend

These models mirror the database schema and enable:
- Alembic autogenerate for migrations
- Type hints and IDE autocomplete
- Optional ORM querying (existing raw SQL still works)

Tables defined:
1. traces - OpenTelemetry-compatible tracing
2. rag_collections - Hierarchical folders with RBAC
3. rag_sources - Ingested documents
4. rag_chunks - Vector embeddings
5. usage_stats - Analytics tracking
6. support_tickets - User support
7. guardrail_violations - Security audit
8. agent_templates - Agent policy definitions
9. agent_instances - Runtime agent instances
10. agent_events - Agent execution audit trail
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, 
    ForeignKey, ARRAY, Index, UniqueConstraint, CheckConstraint,
    DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================================
# TRACING (OpenTelemetry-compatible)
# ============================================================

class Trace(Base):
    """OpenTelemetry-compatible trace/span storage."""
    __tablename__ = "traces"
    
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False)
    span_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(16))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    kind: Mapped[Optional[str]] = mapped_column(String(20))
    start_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    duration_ns: Mapped[Optional[int]] = mapped_column(BigInteger)
    status_code: Mapped[str] = mapped_column(String(10), default="UNSET")
    status_message: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    events: Mapped[list] = mapped_column(JSONB, default=list)
    resource: Mapped[dict] = mapped_column(JSONB, default=dict)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    
    __table_args__ = (
        Index("idx_traces_trace_id", "trace_id"),
        Index("idx_traces_time", "start_time", postgresql_using="btree"),
        Index("idx_traces_user", "user_id"),
    )


# ============================================================
# RAG COLLECTIONS (Hierarchical folders with RBAC)
# ============================================================

class RagCollection(Base):
    """Hierarchical folder structure for RAG sources with RBAC."""
    __tablename__ = "rag_collections"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_collections.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(20), default="personal", nullable=False)
    allowed_roles: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    allowed_teams: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    allowed_users: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    sources: Mapped[List["RagSource"]] = relationship(back_populates="collection")
    children: Mapped[List["RagCollection"]] = relationship(back_populates="parent")
    parent: Mapped[Optional["RagCollection"]] = relationship(
        back_populates="children", remote_side=[id]
    )
    
    __table_args__ = (
        UniqueConstraint("parent_id", "name", "user_id", name="uq_collection_name"),
        Index("idx_rag_collections_parent", "parent_id"),
        Index("idx_rag_collections_user", "user_id"),
        Index("idx_rag_collections_visibility", "visibility"),
    )


# ============================================================
# RAG SOURCES (Ingested documents)
# ============================================================

class RagSource(Base):
    """Ingested document sources for RAG."""
    __tablename__ = "rag_sources"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_collections.id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512))
    storage_type: Mapped[str] = mapped_column(String(20), default="none")
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    
    # Relationships
    collection: Mapped[Optional["RagCollection"]] = relationship(back_populates="sources")
    chunks: Mapped[List["RagChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_rag_sources_user", "user_id"),
        Index("idx_rag_sources_visibility", "visibility"),
        Index("idx_rag_sources_collection", "collection_id"),
    )


# ============================================================
# RAG CHUNKS (Vector embeddings)
# ============================================================

class RagChunk(Base):
    """Vector chunks for RAG retrieval."""
    __tablename__ = "rag_chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(384))  # pgvector type
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer)
    meta_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    
    # Relationships
    source: Mapped[Optional["RagSource"]] = relationship(back_populates="chunks")
    
    __table_args__ = (
        Index("idx_rag_chunks_source", "source_id"),
    )


# ============================================================
# USAGE STATS (Analytics)
# ============================================================

class UsageStats(Base):
    """Usage analytics tracking per user per period."""
    __tablename__ = "usage_stats"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    
    # RAG metrics
    rag_queries: Mapped[int] = mapped_column(Integer, default=0)
    rag_ingestions: Mapped[int] = mapped_column(Integer, default=0)
    rag_chunks_retrieved: Mapped[int] = mapped_column(Integer, default=0)
    
    # Agent metrics
    agent_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    agent_approvals: Mapped[int] = mapped_column(Integer, default=0)
    agent_rejections: Mapped[int] = mapped_column(Integer, default=0)
    
    # LLM metrics
    llm_requests: Mapped[int] = mapped_column(Integer, default=0)
    llm_tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    llm_tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    
    # MCP metrics
    mcp_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_usage_period"),
        Index("idx_usage_stats_user_period", "user_id", "period_start"),
    )


# ============================================================
# SUPPORT TICKETS
# ============================================================

class SupportTicket(Base):
    """User support tickets."""
    __tablename__ = "support_tickets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    
    __table_args__ = (
        Index("idx_tickets_user", "user_id"),
        Index("idx_tickets_status", "status"),
    )


# ============================================================
# GUARDRAIL VIOLATIONS (Security audit)
# ============================================================

class GuardrailViolation(Base):
    """Security guardrail violation audit trail."""
    __tablename__ = "guardrail_violations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    
    __table_args__ = (
        Index("idx_violations_user", "user_id"),
    )


# ============================================================
# AGENT TEMPLATES (Policy definitions)
# ============================================================

class AgentTemplate(Base):
    """Agent policy templates for spawning agents."""
    __tablename__ = "agent_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Ownership & Scope
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="personal")
    
    # Policy Spec
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # RBAC
    required_roles: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    max_template_tools: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    
    # Metadata
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    instances: Mapped[List["AgentInstance"]] = relationship(back_populates="template")
    
    __table_args__ = (
        Index("idx_agent_templates_owner", "owner_id"),
        Index("idx_agent_templates_scope", "scope"),
        Index("idx_agent_templates_org", "org_id"),
    )


# ============================================================
# AGENT INSTANCES (Runtime instances)
# ============================================================

class AgentInstance(Base):
    """Runtime agent instances."""
    __tablename__ = "agent_instances"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="SET NULL")
    )
    template_version: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Ownership & Ancestry
    spawned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    parent_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_instances.id", ondelete="SET NULL")
    )
    root_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    depth: Mapped[int] = mapped_column(Integer, default=0)
    
    # State Machine
    status: Mapped[str] = mapped_column(String(20), default="queued")
    current_state: Mapped[str] = mapped_column(String(20), default="init")
    step: Mapped[int] = mapped_column(Integer, default=0)
    
    # Context & Results
    task: Mapped[Optional[str]] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSONB)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metrics
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=Decimal("0"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    
    # Relationships
    template: Mapped[Optional["AgentTemplate"]] = relationship(back_populates="instances")
    events: Mapped[List["AgentEvent"]] = relationship(back_populates="instance", cascade="all, delete-orphan")
    parent: Mapped[Optional["AgentInstance"]] = relationship(
        back_populates="children", remote_side=[id], foreign_keys=[parent_instance_id]
    )
    children: Mapped[List["AgentInstance"]] = relationship(
        back_populates="parent", foreign_keys=[parent_instance_id]
    )
    
    __table_args__ = (
        Index("idx_agent_instances_status", "status"),
        Index("idx_agent_instances_user", "spawned_by_user_id"),
        Index("idx_agent_instances_parent", "parent_instance_id"),
        Index("idx_agent_instances_template", "template_id"),
    )


# ============================================================
# AGENT EVENTS (Audit trail)
# ============================================================

class AgentEvent(Base):
    """Agent execution audit trail."""
    __tablename__ = "agent_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_instances.id", ondelete="CASCADE")
    )
    
    # Event Data
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Tracing (OpenTelemetry compatible)
    trace_id: Mapped[Optional[str]] = mapped_column(String(32))
    span_id: Mapped[Optional[str]] = mapped_column(String(16))
    
    # Metrics
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    
    # Relationships
    instance: Mapped[Optional["AgentInstance"]] = relationship(back_populates="events")
    
    __table_args__ = (
        Index("idx_agent_events_instance", "instance_id"),
        Index("idx_agent_events_type", "event_type"),
        Index("idx_agent_events_timestamp", "timestamp", postgresql_using="btree"),
    )
