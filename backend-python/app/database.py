"""
Database module for the Python AI Service
Handles PostgreSQL connection with pgvector and tracing
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from typing import AsyncGenerator
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://subba:@localhost:5432/beyondcloud"
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


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
        
        # Create RAG sources table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                file_size INTEGER,
                chunk_count INTEGER DEFAULT 0,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
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
        
        print("✅ Database initialized with pgvector and RAG tables")
