"""
RAG Settings Schema - Pydantic models for RAG configuration
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ContextOrdering(str, Enum):
    SCORE_DESC = "score_desc"  # Highest score first
    SCORE_ASC = "score_asc"    # Lowest score first (for recency)
    POSITION = "position"       # Original document position


class RAGSettingsBase(BaseModel):
    """Base RAG settings (for create/update)"""
    
    # Chunking options
    chunk_size: int = Field(500, ge=100, le=2000, description="Chunk size in characters")
    chunk_overlap: int = Field(50, ge=0, le=500, description="Overlap between chunks")
    use_sentence_boundary: bool = Field(True, description="Split at sentence boundaries")
    
    # Reranking options
    reranker_model: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for reranking"
    )
    rerank_top_k: int = Field(5, ge=1, le=20, description="Number of results after reranking")
    min_score: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relevance score")
    use_reranking: bool = Field(True, description="Enable cross-encoder reranking")
    use_hybrid_search: bool = Field(True, description="Enable BM25 + vector hybrid search")
    bm25_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for BM25 in hybrid search")
    
    # Context assembly
    context_max_tokens: int = Field(4000, ge=500, le=32000, description="Max tokens in context")
    context_ordering: ContextOrdering = Field(
        ContextOrdering.SCORE_DESC,
        description="How to order chunks in context"
    )
    
    # Grounding rules
    require_citations: bool = Field(True, description="Require citations in response")
    max_citations: int = Field(5, ge=1, le=20, description="Maximum citations to include")
    
    # RAG system prompt
    rag_system_prompt: Optional[str] = Field(
        None,
        max_length=4000,
        description="Custom system prompt for RAG queries"
    )


class RAGSettingsResponse(RAGSettingsBase):
    """RAG settings response (includes user_id)"""
    user_id: str
    
    class Config:
        from_attributes = True


class RAGSettingsUpdate(BaseModel):
    """Partial update for RAG settings"""
    chunk_size: Optional[int] = Field(None, ge=100, le=2000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500)
    use_sentence_boundary: Optional[bool] = None
    reranker_model: Optional[str] = None
    rerank_top_k: Optional[int] = Field(None, ge=1, le=20)
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    use_reranking: Optional[bool] = None
    use_hybrid_search: Optional[bool] = None
    bm25_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    context_max_tokens: Optional[int] = Field(None, ge=500, le=32000)
    context_ordering: Optional[ContextOrdering] = None
    require_citations: Optional[bool] = None
    max_citations: Optional[int] = Field(None, ge=1, le=20)
    rag_system_prompt: Optional[str] = Field(None, max_length=4000)


# Default RAG system prompt
DEFAULT_RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

INSTRUCTIONS:
1. Only use information from the provided context to answer questions.
2. If the context doesn't contain enough information, say so clearly.
3. Cite your sources using [1], [2], etc. when referencing specific context chunks.
4. Be concise but thorough.

CONTEXT:
{context}
"""
