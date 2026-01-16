"""
Query Schemas - Request/Response models for Query preprocessing
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class QueryStatus(str, Enum):
    """Status of processed query"""
    READY = "ready"
    PENDING_REVIEW = "pending_review"
    MODIFIED = "modified"
    ORIGINAL = "original"


class QueryCorrection(BaseModel):
    """A single correction made to the query"""
    original: str
    corrected: str
    type: str  # spelling, rewrite, expansion, etc.
    reason: Optional[str] = None


class ProcessQueryRequest(BaseModel):
    """Request to process a query before retrieval"""
    query: str
    context: Optional[str] = None  # Conversation context
    auto_confirm: bool = Field(default=False, description="Skip human confirmation")
    enable_rewrite: bool = Field(default=True, description="Enable LLM query rewriting")
    enable_spell_check: bool = Field(default=True, description="Enable spelling correction")


class ProcessQueryResponse(BaseModel):
    """Response with processed query and modifications"""
    original_query: str
    processed_query: str
    status: QueryStatus
    corrections: List[QueryCorrection]
    confidence: float = Field(ge=0, le=1, description="Confidence in modifications")
    requires_confirmation: bool
    message: str


class ConfirmQueryRequest(BaseModel):
    """Request to confirm or modify a pending query"""
    query_id: str
    confirmed: bool
    modified_query: Optional[str] = Field(
        default=None, 
        description="User's modified version of the query"
    )


class ConfirmQueryResponse(BaseModel):
    """Response after query confirmation"""
    query: str
    status: QueryStatus
    message: str
