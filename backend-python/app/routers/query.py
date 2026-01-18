"""
Query Router - API endpoints for query preprocessing
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.query import (
    ProcessQueryRequest, ProcessQueryResponse,
    ConfirmQueryRequest, ConfirmQueryResponse,
    QueryCorrection, QueryStatus,
)
from app.services.query_service import query_service
from app.tracing import export_spans_to_db
from app.auth import get_current_user_id

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/process", response_model=ProcessQueryResponse)
async def process_query(
    request: ProcessQueryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Process a query before retrieval
    
    This endpoint:
    1. Corrects spelling errors
    2. Rewrites the query for better retrieval using LLM
    3. Returns processed query with status
    
    If significant changes are made and auto_confirm=False,
    the status will be PENDING_REVIEW and requires_confirmation=True.
    The client should show the user the suggested changes and call
    /confirm to proceed.
    """
    result = await query_service.process_query(
        query=request.query,
        context=request.context,
        auto_confirm=request.auto_confirm,
        rewrite=request.enable_rewrite,
        spell_check=request.enable_spell_check,
    )
    
    await export_spans_to_db(db)
    
    # Build message based on status
    if result.status == QueryStatus.PENDING_REVIEW:
        message = "Query was modified. Please review the changes before proceeding."
    elif result.status == QueryStatus.MODIFIED:
        message = f"Query optimized with {len(result.corrections)} modification(s)."
    elif result.status == QueryStatus.ORIGINAL:
        message = "Query is ready for retrieval."
    else:
        message = "Query processed successfully."
    
    return ProcessQueryResponse(
        original_query=result.original_query,
        processed_query=result.processed_query,
        status=result.status,
        corrections=[
            QueryCorrection(
                original=c.get("original", ""),
                corrected=c.get("corrected", ""),
                type=c.get("type", "unknown"),
                reason=c.get("reason"),
            )
            for c in result.corrections
        ],
        confidence=result.confidence,
        requires_confirmation=result.requires_confirmation,
        message=message,
    )


@router.post("/confirm", response_model=ConfirmQueryResponse)
async def confirm_query(
    request: ConfirmQueryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Confirm or modify a pending query
    
    After /process returns requires_confirmation=True, 
    call this endpoint to:
    - Confirm the suggested changes (confirmed=True)
    - Reject and use original (confirmed=False)
    - Provide a custom modification (modified_query="...")
    """
    result = await query_service.confirm_query(
        query_id=request.query_id,
        confirmed=request.confirmed,
        user_modified_query=request.modified_query,
    )
    
    await export_spans_to_db(db)
    
    if request.modified_query:
        message = "Using your modified query."
    elif request.confirmed:
        message = "Query changes confirmed."
    else:
        message = "Using original query."
    
    return ConfirmQueryResponse(
        query=result.processed_query or request.modified_query or "",
        status=result.status,
        message=message,
    )


@router.post("/process-and-retrieve")
async def process_and_retrieve(
    request: ProcessQueryRequest,
    top_k: int = 5,
    min_score: float = 0.5,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Convenience endpoint: Process query and retrieve in one call
    
    Only works when auto_confirm=True or no confirmation needed.
    Otherwise, returns the processed query for review.
    """
    from app.services.rag_service import rag_service
    
    # Process query
    processed = await query_service.process_query(
        query=request.query,
        context=request.context,
        auto_confirm=request.auto_confirm,
        rewrite=request.enable_rewrite,
        spell_check=request.enable_spell_check,
    )
    
    # If confirmation needed, return early
    if processed.requires_confirmation:
        await export_spans_to_db(db)
        return {
            "status": "pending_review",
            "processed_query": processed.processed_query,
            "corrections": processed.corrections,
            "message": "Please confirm the query modifications before retrieval.",
        }
    
    # Retrieve with processed query
    chunks = await rag_service.retrieve(
        db=db,
        user_id=user_id,
        query=processed.processed_query,
        top_k=top_k,
        min_score=min_score,
    )
    
    await export_spans_to_db(db)
    
    return {
        "status": "completed",
        "original_query": processed.original_query,
        "processed_query": processed.processed_query,
        "corrections": processed.corrections,
        "chunks": [
            {
                "id": str(c["id"]),
                "source_id": str(c["source_id"]),
                "source_name": c["source_name"],
                "content": c["content"],
                "score": c["score"],
            }
            for c in chunks
        ],
    }
