"""
RAG Router - API endpoints for document management and retrieval
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database import get_db
from app.schemas.rag import (
    SourceResponse, IngestRequest, IngestResponse,
    QueryRequest, QueryResponse, RetrieveRequest, ChunkResponse
)
from app.services.rag_service import rag_service
from app.tracing import export_spans_to_db

router = APIRouter(prefix="/rag", tags=["RAG"])

# TODO: Replace with actual auth middleware
async def get_current_user_id() -> str:
    """Temporary: Get user ID from auth (hardcoded for now)"""
    return "00000000-0000-0000-0000-000000000001"


@router.get("/sources", response_model=List[SourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all document sources for the current user"""
    sources = await rag_service.list_sources(db, user_id)
    await export_spans_to_db(db)
    return sources


@router.post("/ingest", response_model=IngestResponse)
async def ingest_text(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Ingest text content into the RAG system"""
    result = await rag_service.ingest_text(
        db=db,
        user_id=user_id,
        name=request.name,
        content=request.content,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        metadata=request.metadata,
    )
    await export_spans_to_db(db)
    return IngestResponse(
        source_id=result["source_id"],
        name=result["name"],
        chunk_count=result["chunk_count"],
        message=f"Successfully ingested {result['chunk_count']} chunks",
    )


@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Upload and ingest a document file"""
    # Read file content
    content = await file.read()
    
    # Detect file type and extract text
    filename = file.filename or "uploaded_file"
    
    if filename.endswith(".txt"):
        text_content = content.decode("utf-8")
    elif filename.endswith(".md"):
        text_content = content.decode("utf-8")
    elif filename.endswith(".pdf"):
        # Extract text from PDF
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text_content = "\n".join(page.extract_text() for page in reader.pages)
    elif filename.endswith(".docx"):
        # Extract text from DOCX
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        text_content = "\n".join(para.text for para in doc.paragraphs)
    else:
        # Try as plain text
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "Unsupported file type")
    
    result = await rag_service.ingest_text(
        db=db,
        user_id=user_id,
        name=filename,
        content=text_content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        metadata={"original_filename": filename, "file_size": len(content)},
    )
    await export_spans_to_db(db)
    return IngestResponse(
        source_id=result["source_id"],
        name=result["name"],
        chunk_count=result["chunk_count"],
        message=f"Successfully ingested {result['chunk_count']} chunks from {filename}",
    )


@router.post("/retrieve", response_model=List[ChunkResponse])
async def retrieve(
    request: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Vector similarity search - retrieve relevant chunks"""
    chunks = await rag_service.retrieve(
        db=db,
        user_id=user_id,
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
        source_ids=[str(s) for s in request.source_ids] if request.source_ids else None,
    )
    await export_spans_to_db(db)
    return [
        ChunkResponse(
            id=c["id"],
            source_id=c["source_id"],
            content=c["content"],
            score=c["score"],
            metadata={**c["metadata"], "source_name": c["source_name"]},
        )
        for c in chunks
    ]


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """RAG query - retrieve and optionally generate answer"""
    # Retrieve relevant chunks
    chunks = await rag_service.retrieve(
        db=db,
        user_id=user_id,
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
    )
    
    await export_spans_to_db(db)
    
    # TODO: Add LLM generation with context
    return QueryResponse(
        query=request.query,
        chunks=[
            ChunkResponse(
                id=c["id"],
                source_id=c["source_id"],
                content=c["content"],
                score=c["score"],
                metadata={**c["metadata"], "source_name": c["source_name"]},
            )
            for c in chunks
        ],
        answer=None,  # Will be filled by LLM in next iteration
    )


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a document source and all its chunks"""
    deleted = await rag_service.delete_source(db, user_id, source_id)
    if not deleted:
        raise HTTPException(404, "Source not found")
    return {"message": "Source deleted successfully"}
