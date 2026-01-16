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
    generate: bool = Field(default=True, description="Generate answer using LLM")
    # Hybrid search options
    use_hybrid: bool = Field(default=True, description="Use BM25+vector hybrid search")
    use_reranking: bool = Field(default=True, description="Apply cross-encoder reranking")
    bm25_weight: float = Field(default=0.3, ge=0, le=1, description="BM25 weight in hybrid search")


class Citation(BaseModel):
    """Source citation for answer"""
    source_id: str
    source_name: str
    score: float
    content_preview: str


class QueryResponse(BaseModel):
    """RAG query response"""
    query: str
    chunks: List[ChunkResponse]
    answer: Optional[str] = None
    citations: List[Citation] = []
    model: Optional[str] = None
    error: Optional[str] = None
    # Search metadata
    search_mode: Optional[str] = None  # "vector", "hybrid", "hybrid+rerank"


class RetrieveRequest(BaseModel):
    """Vector search only request"""
    query: str
    top_k: int = 5
    min_score: float = 0.5
    source_ids: Optional[List[UUID]] = None  # Filter by sources
    # Hybrid search options
    use_hybrid: bool = Field(default=False, description="Use BM25+vector hybrid search")
    use_reranking: bool = Field(default=False, description="Apply cross-encoder reranking")
    bm25_weight: float = Field(default=0.3, ge=0, le=1, description="BM25 weight in hybrid search")
