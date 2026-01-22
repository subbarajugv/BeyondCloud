"""
Database module for the Python AI Service
Handles PostgreSQL connection with pgvector and tracing
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, create_engine
from sqlmodel import Session
from contextlib import contextmanager
from typing import AsyncGenerator, Generator

from app.config import get_settings

settings = get_settings()
DATABASE_URL = settings.database_url

# Async engine for FastAPI/SQLAlchemy with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,           # Number of connections to keep in pool
    max_overflow=20,        # Max additional connections beyond pool_size
    pool_timeout=30,        # Seconds to wait for a connection
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True,     # Validate connections before use
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for SQLModel (uses psycopg2) with connection pooling
sync_engine = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency for getting database sessions (SQLAlchemy)"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db for compatibility"""
    async with async_session() as session:
        yield session


@contextmanager
def get_session_sync() -> Generator[Session, None, None]:
    """Sync session context manager for SQLModel-based code"""
    with Session(sync_engine) as session:
        yield session


async def init_database():
    """Initialize database with required extensions and tables"""
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create traces table (OTel-compatible)
        await conn.execute(text("""
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
        """))
        
        # Create indexes for traces
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_traces_time ON traces(start_time DESC)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_traces_user ON traces(user_id)
        """))
        
        # Create RAG collections table (hierarchical folders with RBAC)
        await conn.execute(text("""
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
        """))
        
        # Create indexes for collections
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_collections_parent ON rag_collections(parent_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_collections_user ON rag_collections(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_collections_visibility ON rag_collections(visibility)
        """))
        
        # Create RAG sources table
        await conn.execute(text("""
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
        """))
        
        # Add new columns if they don't exist (migration for existing tables)
        await conn.execute(text("""
            ALTER TABLE rag_sources 
            ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'private' NOT NULL
        """))
        await conn.execute(text("""
            ALTER TABLE rag_sources 
            ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES rag_collections(id) ON DELETE SET NULL
        """))
        await conn.execute(text("""
            ALTER TABLE rag_sources 
            ADD COLUMN IF NOT EXISTS storage_key VARCHAR(512)
        """))
        await conn.execute(text("""
            ALTER TABLE rag_sources 
            ADD COLUMN IF NOT EXISTS storage_type VARCHAR(20) DEFAULT 'none'
        """))
        
        # Create RAG chunks table with vector embeddings
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID REFERENCES rag_sources(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                embedding vector(384),
                chunk_index INTEGER,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        # Create indexes for vector search
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks(source_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_sources_user ON rag_sources(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_sources_visibility ON rag_sources(visibility)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_sources_collection ON rag_sources(collection_id)
        """))

        # Create usage tracking table for analytics
        await conn.execute(text("""
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
        """))

        # Create indexes for usage stats
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_usage_stats_user_period ON usage_stats(user_id, period_start)
        """))
        
        # Create support tickets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                subject VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'open',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                resolved_at TIMESTAMPTZ
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)
        """))

        # Create guardrail violations table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS guardrail_violations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                details JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_violations_user ON guardrail_violations(user_id)
        """))
        
        # ============================================================
        # AGENT SPAWNING TABLES
        # ============================================================
        
        # Agent Templates - Policy definitions for agents
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL,
                description TEXT,
                
                -- Ownership & Scope
                owner_id UUID NOT NULL,
                org_id UUID,
                scope VARCHAR(20) NOT NULL DEFAULT 'personal',
                
                -- Policy Spec (JSON)
                spec JSONB NOT NULL,
                version INTEGER DEFAULT 1,
                
                -- RBAC
                required_roles TEXT[] DEFAULT '{}',
                max_template_tools TEXT[] DEFAULT '{}',
                
                -- Metadata
                icon VARCHAR(50),
                color VARCHAR(20),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_templates_owner ON agent_templates(owner_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_templates_scope ON agent_templates(scope)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_templates_org ON agent_templates(org_id)
        """))
        
        # Agent Instances - Runtime instances of agents
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_instances (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                template_id UUID REFERENCES agent_templates(id) ON DELETE SET NULL,
                template_version INTEGER,
                
                -- Ownership & Ancestry
                spawned_by_user_id UUID NOT NULL,
                org_id UUID,
                parent_instance_id UUID REFERENCES agent_instances(id) ON DELETE SET NULL,
                root_instance_id UUID,
                depth INTEGER DEFAULT 0,
                
                -- State Machine
                status VARCHAR(20) DEFAULT 'queued',
                current_state VARCHAR(20) DEFAULT 'init',
                step INTEGER DEFAULT 0,
                
                -- Context & Results
                task TEXT,
                context JSONB DEFAULT '{}',
                result JSONB,
                error TEXT,
                
                -- Metrics
                tokens_used INTEGER DEFAULT 0,
                cost_usd DECIMAL(10,6) DEFAULT 0,
                
                -- Timestamps
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_instances_status ON agent_instances(status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_instances_user ON agent_instances(spawned_by_user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_instances_parent ON agent_instances(parent_instance_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_instances_template ON agent_instances(template_id)
        """))
        
        # Agent Events - Audit trail for agent execution
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                instance_id UUID REFERENCES agent_instances(id) ON DELETE CASCADE,
                
                -- Event Data
                event_type VARCHAR(50) NOT NULL,
                payload JSONB DEFAULT '{}',
                
                -- Tracing (OpenTelemetry compatible)
                trace_id VARCHAR(32),
                span_id VARCHAR(16),
                
                -- Metrics
                tokens_used INTEGER DEFAULT 0,
                latency_ms INTEGER,
                
                -- Timestamp
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_events_instance ON agent_events(instance_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent_events(event_type)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp DESC)
        """))
        
        print("✅ Database initialized with pgvector, RAG collections, usage stats, storage, dashboard, and agent spawning tables")

