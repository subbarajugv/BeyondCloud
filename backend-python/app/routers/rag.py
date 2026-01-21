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
    QueryRequest, QueryResponse, RetrieveRequest, ChunkResponse, Citation,
    VisibilityUpdate
)
from app.services.rag_service import rag_service
from app.services.answer_service import answer_service
from app.services.rag_guardrails import validate_query, validate_response, sanitize_query
from app.tracing import export_spans_to_db
from app.auth import get_current_user_id
from app.role_check import get_current_user_with_role, require_min_role, has_min_role, UserWithRole

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/sources", response_model=List[SourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all document sources accessible to the current user (private + shared)"""
    sources = await rag_service.list_sources(db, user_id)
    await export_spans_to_db(db)
    return sources


@router.post("/ingest", response_model=IngestResponse)
async def ingest_text(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """
    Ingest text content into the RAG system.
    
    Visibility options:
    - private: Only the user can see this source (default)
    - shared: All users can see this source (requires admin role)
    """
    # Only admins can create shared sources
    if request.visibility == "shared" and not has_min_role(user.role, "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only admins can create shared knowledge bases"
        )
    
    result = await rag_service.ingest_text(
        db=db,
        user_id=user.id,
        name=request.name,
        content=request.content,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        visibility=request.visibility,
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
    visibility: str = Form("private"),
    collection_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """
    Upload and ingest a document file.
    
    Visibility options:
    - private: Only the user can see this source (default)
    - shared: All users can see this source (requires admin role)
    
    The original file is stored and can be downloaded later.
    """
    # Only admins can create shared sources
    if visibility == "shared" and not has_min_role(user.role, "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only admins can create shared knowledge bases"
        )
    
    # Read file content
    file_bytes = await file.read()
    
    # Detect file type and extract text
    filename = file.filename or "uploaded_file"
    
    if filename.endswith(".txt"):
        text_content = file_bytes.decode("utf-8")
    elif filename.endswith(".md"):
        text_content = file_bytes.decode("utf-8")
    elif filename.endswith(".pdf"):
        # Extract text from PDF
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        text_content = "\n".join(page.extract_text() for page in reader.pages)
    elif filename.endswith(".docx"):
        # Extract text from DOCX
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        text_content = "\n".join(para.text for para in doc.paragraphs)
    elif filename.endswith(".html") or filename.endswith(".htm"):
        # Extract text from HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(file_bytes.decode("utf-8"), "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        text_content = soup.get_text(separator="\n", strip=True)
    else:
        # Try as plain text
        try:
            text_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "Unsupported file type")
    
    result = await rag_service.ingest_text(
        db=db,
        user_id=user.id,
        name=filename,
        content=text_content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        visibility=visibility,
        metadata={"original_filename": filename, "file_size": len(file_bytes)},
        file_content=file_bytes,  # Store original file for download
        collection_id=collection_id,
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
    """RAG query - retrieve with hybrid search and optionally generate answer"""
    
    # ========== GUARDRAIL: Validate query ==========
    is_valid, block_reason, warnings = validate_query(request.query)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "QUERY_BLOCKED",
                "message": block_reason,
            }
        )
    
    # Sanitize query
    sanitized_query = sanitize_query(request.query)
    # ========== END GUARDRAIL ==========
    
    # Determine search mode
    search_mode = "vector"
    if request.use_hybrid:
        search_mode = "hybrid+rerank" if request.use_reranking else "hybrid"
    elif request.use_reranking:
        search_mode = "vector+rerank"
    
    # Use hybrid retrieve if any advanced options enabled
    if request.use_hybrid or request.use_reranking:
        chunks = await rag_service.hybrid_retrieve(
            db=db,
            user_id=user_id,
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
            use_reranking=request.use_reranking,
            use_hybrid=request.use_hybrid,
            bm25_weight=request.bm25_weight,
        )
    else:
        # Basic vector search
        chunks = await rag_service.retrieve(
            db=db,
            user_id=user_id,
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
        )
    
    # Build chunk responses
    chunk_responses = [
        ChunkResponse(
            id=c["id"],
            source_id=c["source_id"],
            content=c["content"],
            score=c.get("rerank_score", c.get("score", 0)),
            metadata={**c.get("metadata", {}), "source_name": c.get("source_name", "")},
        )
        for c in chunks
    ]
    
    # Generate answer if requested
    answer = None
    citations = []
    model = None
    error = None
    
    if request.generate and chunks:
        result = await answer_service.generate_answer(
            db=db,
            user_id=user_id,
            query=request.query,
            chunks=chunks,
        )
        answer = result.answer
        citations = [
            Citation(
                source_id=c["source_id"],
                source_name=c["source_name"],
                score=c["score"],
                content_preview=c.get("content_preview", c.get("content", "")[:100]),
            )
            for c in result.citations
        ]
        model = result.model
        error = result.error
    
    await export_spans_to_db(db)
    
    return QueryResponse(
        query=request.query,
        chunks=chunk_responses,
        answer=answer,
        citations=citations,
        model=model,
        error=error,
        search_mode=search_mode,
    )


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """
    Delete a document source and all its chunks.
    
    - Users can only delete their own sources
    - Admins can delete any source
    """
    # Check if user owns the source or is an admin
    source = await rag_service.get_source(db, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    
    is_owner = source["user_id"] == user.id
    is_admin = has_min_role(user.role, "admin")
    
    if not is_owner and not is_admin:
        raise HTTPException(403, "You can only delete your own sources")
    
    # For owners, use their ID; for admins deleting others' sources, bypass ownership check
    if is_owner:
        deleted = await rag_service.delete_source(db, user.id, source_id)
    else:
        # Admin deleting someone else's source - bypass ownership check
        from sqlalchemy import text
        result = await db.execute(
            text("DELETE FROM rag_sources WHERE id = :source_id RETURNING id"),
            {"source_id": source_id}
        )
        await db.commit()
        deleted = result.rowcount > 0
    
    if not deleted:
        raise HTTPException(404, "Source not found")
    return {"message": "Source deleted successfully"}


@router.put("/sources/{source_id}/visibility")
async def update_source_visibility(
    source_id: str,
    request: VisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(require_min_role("admin")),
):
    """
    Update source visibility (admin only).
    
    Change a source between private and shared visibility.
    """
    source = await rag_service.get_source(db, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    
    updated = await rag_service.update_visibility(db, source_id, request.visibility)
    if not updated:
        raise HTTPException(500, "Failed to update visibility")
    
    return {
        "message": f"Source visibility updated to '{request.visibility}'",
        "source_id": source_id,
        "visibility": request.visibility
    }


# ========== Embedding Models Endpoint ==========

from app.services.embedding_service import EmbeddingService, EMBEDDING_MODELS


@router.get("/embedding-models")
async def list_embedding_models(
    provider: str = None,
):
    """
    List available embedding models by provider.
    
    Query params:
    - provider: Filter by provider (sentence_transformers, openai, ollama)
    """
    if provider:
        if provider not in EMBEDDING_MODELS:
            return {"error": f"Unknown provider: {provider}", "available": list(EMBEDDING_MODELS.keys())}
        return {
            "provider": provider,
            "models": [
                {"name": name, "dimensions": dims}
                for name, dims in EMBEDDING_MODELS[provider].items()
            ]
        }
    
    return {
        "providers": [
            {
                "name": p,
                "models": [{"name": m, "dimensions": d} for m, d in models.items()]
            }
            for p, models in EMBEDDING_MODELS.items()
        ]
    }


# ========== RAG Settings Endpoints ==========

from app.schemas.rag_settings import RAGSettingsBase, RAGSettingsUpdate, RAGSettingsResponse
from sqlalchemy import text


@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get user's RAG settings"""
    result = await db.execute(
        text("SELECT * FROM rag_settings WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    row = result.fetchone()
    
    if not row:
        # Return defaults
        return RAGSettingsBase().model_dump()
    
    return dict(row._mapping)


@router.put("/settings")
async def update_settings(
    settings: RAGSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update user's RAG settings (upsert)"""
    # Filter out None values
    updates = {k: v for k, v in settings.model_dump().items() if v is not None}
    
    if not updates:
        raise HTTPException(400, "No settings provided")
    
    # Check if settings exist
    result = await db.execute(
        text("SELECT user_id FROM rag_settings WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    exists = result.fetchone() is not None
    
    if exists:
        # Update
        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        await db.execute(
            text(f"UPDATE rag_settings SET {set_clause}, updated_at = NOW() WHERE user_id = :user_id"),
            {"user_id": user_id, **updates}
        )
    else:
        # Insert with defaults + updates
        defaults = RAGSettingsBase().model_dump()
        defaults.update(updates)
        
        columns = ["user_id"] + list(defaults.keys())
        values = [":user_id"] + [f":{k}" for k in defaults.keys()]
        
        await db.execute(
            text(f"INSERT INTO rag_settings ({', '.join(columns)}) VALUES ({', '.join(values)})"),
            {"user_id": user_id, **defaults}
        )
    
    await db.commit()
    
    # Return updated settings
    return await get_settings(db, user_id)


# ========== Collection Endpoints ==========

from app.services.collection_service import collection_service
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List as TypingList

class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    visibility: str = "personal"
    allowed_roles: Optional[TypingList[str]] = None
    allowed_teams: Optional[TypingList[str]] = None
    allowed_users: Optional[TypingList[str]] = None

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    allowed_roles: Optional[TypingList[str]] = None
    allowed_teams: Optional[TypingList[str]] = None
    allowed_users: Optional[TypingList[str]] = None

class CollectionMove(BaseModel):
    new_parent_id: Optional[str] = None


@router.get("/collections")
async def list_collections(
    tree: bool = False,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """List all collections accessible to the current user"""
    user_roles = [user.role] if user.role else []
    
    if tree:
        return await collection_service.list_tree(db, user.id, user_roles)
    else:
        return await collection_service.list_accessible(db, user.id, user_roles)


@router.post("/collections")
async def create_collection(
    request: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """Create a new collection"""
    # Only admins can create non-personal collections
    if request.visibility != "personal" and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Only admins can create public/role/team collections")
    
    return await collection_service.create(
        db=db,
        user_id=user.id,
        name=request.name,
        parent_id=request.parent_id,
        description=request.description,
        visibility=request.visibility,
        allowed_roles=request.allowed_roles,
        allowed_teams=request.allowed_teams,
        allowed_users=request.allowed_users,
    )


@router.get("/collections/{collection_id}")
async def get_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific collection"""
    collection = await collection_service.get(db, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    return collection


@router.put("/collections/{collection_id}")
async def update_collection(
    collection_id: str,
    request: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """Update a collection"""
    collection = await collection_service.get(db, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    
    # Only owner or admin can update
    is_owner = collection["user_id"] == user.id
    if not is_owner and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Permission denied")
    
    # Only admins can change visibility from personal
    if request.visibility and request.visibility != "personal" and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Only admins can set non-personal visibility")
    
    await collection_service.update(
        db=db,
        collection_id=collection_id,
        name=request.name,
        description=request.description,
        visibility=request.visibility,
        allowed_roles=request.allowed_roles,
        allowed_teams=request.allowed_teams,
        allowed_users=request.allowed_users,
    )
    return {"message": "Collection updated", "collection_id": collection_id}


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """Delete a collection (cascades to children and sources)"""
    collection = await collection_service.get(db, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    
    # Only owner or admin can delete
    is_owner = collection["user_id"] == user.id
    if not is_owner and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Permission denied")
    
    deleted = await collection_service.delete(db, collection_id, user.id if is_owner else collection["user_id"])
    if not deleted:
        raise HTTPException(500, "Failed to delete collection")
    
    return {"message": "Collection deleted", "collection_id": collection_id}


@router.post("/collections/{collection_id}/move")
async def move_collection(
    collection_id: str,
    request: CollectionMove,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """Move a collection to a new parent"""
    collection = await collection_service.get(db, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    
    if collection["user_id"] != user.id and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Permission denied")
    
    try:
        await collection_service.move(db, collection_id, request.new_parent_id)
        return {"message": "Collection moved", "collection_id": collection_id, "new_parent_id": request.new_parent_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ========== File Download ==========

@router.get("/sources/{source_id}/download")
async def download_source_file(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(get_current_user_with_role),
):
    """Download the original file for a source"""
    source = await rag_service.get_source(db, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    
    # Check access
    is_owner = source["user_id"] == user.id
    is_shared = source["visibility"] == "shared"
    if not is_owner and not is_shared and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Permission denied")
    
    result = await rag_service.download_source(db, source_id)
    if not result:
        raise HTTPException(404, "No file stored for this source")
    
    file_bytes, filename = result
    
    # Determine content type
    content_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.endswith(".txt") or filename.endswith(".md"):
        content_type = "text/plain"
    elif filename.endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
