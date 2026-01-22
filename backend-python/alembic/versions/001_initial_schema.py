"""Initial schema - baseline from existing database

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-23

This migration captures the existing database schema as a baseline.
It uses IF NOT EXISTS to be safe for existing databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables if they don't exist (baseline migration)."""
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # ============================================================
    # TRACING TABLE (OTel-compatible)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            trace_id VARCHAR(32) NOT NULL,
            span_id VARCHAR(16) PRIMARY KEY,
            parent_span_id VARCHAR(16),
            name VARCHAR(255),
            kind VARCHAR(20),
            start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            end_time TIMESTAMPTZ,
            duration_ns BIGINT,
            status_code VARCHAR(10) DEFAULT 'UNSET',
            status_message TEXT,
            attributes JSONB DEFAULT '{}',
            events JSONB DEFAULT '[]',
            resource JSONB DEFAULT '{}',
            user_id UUID
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_traces_time ON traces(start_time DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_traces_user ON traces(user_id)")
    
    # ============================================================
    # RAG COLLECTIONS (hierarchical folders with RBAC)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_collections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parent_id UUID REFERENCES rag_collections(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            visibility VARCHAR(20) DEFAULT 'personal' NOT NULL,
            allowed_roles TEXT[] DEFAULT '{}',
            allowed_teams UUID[] DEFAULT '{}',
            allowed_users UUID[] DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(parent_id, name, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_collections_parent ON rag_collections(parent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_collections_user ON rag_collections(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_collections_visibility ON rag_collections(visibility)")
    
    # ============================================================
    # RAG SOURCES
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            collection_id UUID REFERENCES rag_collections(id) ON DELETE SET NULL,
            user_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            visibility VARCHAR(20) DEFAULT 'private' NOT NULL,
            storage_key VARCHAR(512),
            storage_type VARCHAR(20) DEFAULT 'none',
            file_size INTEGER,
            chunk_count INTEGER DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_sources_user ON rag_sources(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_sources_visibility ON rag_sources(visibility)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_sources_collection ON rag_sources(collection_id)")
    
    # ============================================================
    # RAG CHUNKS (with vector embeddings)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID REFERENCES rag_sources(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding vector(384),
            chunk_index INTEGER,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks(source_id)")
    
    # ============================================================
    # USAGE STATS (analytics)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            rag_queries INTEGER DEFAULT 0,
            rag_ingestions INTEGER DEFAULT 0,
            rag_chunks_retrieved INTEGER DEFAULT 0,
            agent_tool_calls INTEGER DEFAULT 0,
            agent_approvals INTEGER DEFAULT 0,
            agent_rejections INTEGER DEFAULT 0,
            llm_requests INTEGER DEFAULT 0,
            llm_tokens_input INTEGER DEFAULT 0,
            llm_tokens_output INTEGER DEFAULT 0,
            mcp_tool_calls INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, period_start, period_end)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_stats_user_period ON usage_stats(user_id, period_start)")
    
    # ============================================================
    # SUPPORT TICKETS
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            subject VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'open',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            resolved_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)")
    
    # ============================================================
    # GUARDRAIL VIOLATIONS
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS guardrail_violations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            details JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_violations_user ON guardrail_violations(user_id)")
    
    # ============================================================
    # AGENT TEMPLATES (policy definitions)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            description TEXT,
            owner_id UUID NOT NULL,
            org_id UUID,
            scope VARCHAR(20) NOT NULL DEFAULT 'personal',
            spec JSONB NOT NULL,
            version INTEGER DEFAULT 1,
            required_roles TEXT[] DEFAULT '{}',
            max_template_tools TEXT[] DEFAULT '{}',
            icon VARCHAR(50),
            color VARCHAR(20),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_templates_owner ON agent_templates(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_templates_scope ON agent_templates(scope)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_templates_org ON agent_templates(org_id)")
    
    # ============================================================
    # AGENT INSTANCES (runtime instances)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_instances (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID REFERENCES agent_templates(id) ON DELETE SET NULL,
            template_version INTEGER,
            spawned_by_user_id UUID NOT NULL,
            org_id UUID,
            parent_instance_id UUID REFERENCES agent_instances(id) ON DELETE SET NULL,
            root_instance_id UUID,
            depth INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'queued',
            current_state VARCHAR(20) DEFAULT 'init',
            step INTEGER DEFAULT 0,
            task TEXT,
            context JSONB DEFAULT '{}',
            result JSONB,
            error TEXT,
            tokens_used INTEGER DEFAULT 0,
            cost_usd DECIMAL(10,6) DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_instances_status ON agent_instances(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_instances_user ON agent_instances(spawned_by_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_instances_parent ON agent_instances(parent_instance_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_instances_template ON agent_instances(template_id)")
    
    # ============================================================
    # AGENT EVENTS (audit trail)
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instance_id UUID REFERENCES agent_instances(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            payload JSONB DEFAULT '{}',
            trace_id VARCHAR(32),
            span_id VARCHAR(16),
            tokens_used INTEGER DEFAULT 0,
            latency_ms INTEGER,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_events_instance ON agent_events(instance_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent_events(event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp DESC)")


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.execute("DROP TABLE IF EXISTS agent_events CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_instances CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS guardrail_violations CASCADE")
    op.execute("DROP TABLE IF EXISTS support_tickets CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS rag_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS rag_sources CASCADE")
    op.execute("DROP TABLE IF EXISTS rag_collections CASCADE")
    op.execute("DROP TABLE IF EXISTS traces CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")
