"""
RAG Schemas - Request/Response models for RAG endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class SourceCreate(BaseModel):
    """Request to create a document source"""
    name: str
    type: str = "file"  # file, url, text
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceResponse(BaseModel):
    """Document source response"""
    id: UUID
    user_id: UUID
    name: str
    type: str
    file_size: Optional[int] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChunkResponse(BaseModel):
    """Retrieved chunk response"""
    id: UUID
    source_id: UUID
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """Request to ingest text content"""
    name: str
    content: str
    chunk_size: int = 500
    chunk_overlap: int = 50
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    """Ingestion response"""
    source_id: UUID
    name: str
    chunk_count: int
    message: str


class QueryRequest(BaseModel):
    """RAG query request"""
    query: str
    top_k: int = 5
    min_score: float = 0.5
    include_sources: bool = True


class QueryResponse(BaseModel):
    """RAG query response"""
    query: str
    chunks: List[ChunkResponse]
    answer: Optional[str] = None  # Filled if generate=True


class RetrieveRequest(BaseModel):
    """Vector search only request"""
    query: str
    top_k: int = 5
    min_score: float = 0.5
    source_ids: Optional[List[UUID]] = None  # Filter by sources
