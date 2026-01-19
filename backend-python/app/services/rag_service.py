"""
RAG Service - Document ingestion, embedding, and retrieval
"""
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tracing import create_span, tracer
from app.config import get_settings
from app.services.storage_service import get_storage_service
from app.services.usage_service import usage_service


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) Service
    
    Handles:
    - Document ingestion (chunking + embedding)
    - Vector similarity search
    - Source management
    """
    
    def __init__(self):
        self._embedder = None
    
    async def get_embedder(self):
        """Lazy-load the embedding model from config"""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            settings = get_settings()
            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50
    ) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_len:
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - chunk_overlap
        
        return [c for c in chunks if c]  # Remove empty chunks
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        embedder = await self.get_embedder()
        embeddings = embedder.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    async def ingest_text(
        self,
        db: AsyncSession,
        user_id: str,
        name: str,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        visibility: str = "private",
        metadata: Optional[Dict[str, Any]] = None,
        file_content: Optional[bytes] = None,  # Original file bytes for storage
        collection_id: Optional[str] = None,  # Collection to add source to
    ) -> Dict[str, Any]:
        """
        Ingest text content: chunk, embed, and store
        
        Args:
            visibility: 'private' (user only) or 'shared' (all users)
        """
        async with create_span("rag.ingest", {"name": name, "content_length": len(content), "visibility": visibility}) as span:
            # Store original file if provided
            storage_key = None
            storage_type = "none"
            if file_content:
                storage = get_storage_service()
                storage_key = await storage.upload(file_content, name, user_id)
                storage_type = get_settings().storage_type
                span.set_attribute("storage_type", storage_type)
            
            # Create source record
            source_id = uuid.uuid4()
            await db.execute(
                text("""
                    INSERT INTO rag_sources (id, user_id, name, type, visibility, file_size, metadata, collection_id, storage_key, storage_type)
                    VALUES (:id, :user_id, :name, :type, :visibility, :file_size, :metadata, :collection_id, :storage_key, :storage_type)
                """),
                {
                    "id": str(source_id),
                    "user_id": user_id,
                    "name": name,
                    "type": "text",
                    "visibility": visibility,
                    "file_size": len(content),
                    "metadata": json.dumps(metadata or {}),
                    "collection_id": collection_id,
                    "storage_key": storage_key,
                    "storage_type": storage_type,
                }
            )
            
            # Chunk the content
            span.add_event("chunking")
            chunks = self.chunk_text(content, chunk_size, chunk_overlap)
            span.set_attribute("chunk_count", len(chunks))
            
            # Generate embeddings
            span.add_event("embedding")
            embeddings = await self.embed_texts(chunks)
            
            # Store chunks with embeddings
            span.add_event("storing")
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Format embedding as PostgreSQL vector string
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await db.execute(
                    text("""
                        INSERT INTO rag_chunks (id, source_id, content, embedding, chunk_index, metadata)
                        VALUES (:id, :source_id, :content, CAST(:embedding AS vector), :chunk_index, :metadata)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "source_id": str(source_id),
                        "content": chunk,
                        "embedding": embedding_str,
                        "chunk_index": i,
                        "metadata": json.dumps({"position": i}),
                    }
                )
            
            # Update chunk count
            await db.execute(
                text("UPDATE rag_sources SET chunk_count = :count WHERE id = :id"),
                {"count": len(chunks), "id": str(source_id)}
            )
            
            await db.commit()

            # Tracking: Increment RAG ingestion
            await usage_service.increment(db, user_id, "rag_ingestions")
            
            return {
                "source_id": source_id,
                "name": name,
                "chunk_count": len(chunks),
            }
    
    async def retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        source_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search across user's private sources and all shared sources
        """
        async with create_span("rag.retrieve", {"query": query, "top_k": top_k}) as span:
            # Embed query
            span.add_event("embedding_query")
            query_embedding = (await self.embed_texts([query]))[0]
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            # Tracking: Increment RAG query
            await usage_service.increment(db, user_id, "rag_queries")
            
            # Build query with optional source filter
            source_filter = ""
            params = {
                "embedding": embedding_str,
                "user_id": user_id,
                "limit": top_k,
                "min_score": min_score,
            }
            
            if source_ids:
                source_filter = "AND c.source_id = ANY(:source_ids)"
                params["source_ids"] = [str(sid) for sid in source_ids]
            
            # Vector similarity search using pgvector
            # Include user's private sources AND all shared sources
            span.add_event("vector_search")
            result = await db.execute(
                text(f"""
                    SELECT 
                        c.id,
                        c.source_id,
                        c.content,
                        c.metadata,
                        s.name as source_name,
                        1 - (c.embedding <=> CAST(:embedding AS vector)) as score
                    FROM rag_chunks c
                    JOIN rag_sources s ON c.source_id = s.id
                    WHERE (s.user_id = :user_id OR s.visibility = 'shared')
                    {source_filter}
                    AND 1 - (c.embedding <=> CAST(:embedding AS vector)) >= :min_score
                    ORDER BY c.embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                """),
                params
            )
            
            rows = result.mappings().all()
            chunks = [
                {
                    "id": str(row["id"]),
                    "source_id": str(row["source_id"]),
                    "source_name": row["source_name"],
                    "content": row["content"],
                    "score": float(row["score"]),
                    "metadata": row["metadata"],
                }
                for row in rows
            ]
            
            span.set_attribute("result_count", len(chunks))

            # Tracking: Increment chunks retrieved
            if chunks:
                await usage_service.increment(db, user_id, "rag_chunks_retrieved", amount=len(chunks))
                
            return chunks
    
    async def hybrid_retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        source_ids: Optional[List[str]] = None,
        use_reranking: bool = True,
        use_hybrid: bool = True,
        bm25_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Advanced retrieval with hybrid search and reranking
        
        Combines:
        1. Vector search (pgvector or FAISS)
        2. BM25 keyword search
        3. Reciprocal Rank Fusion
        4. Cross-encoder reranking
        
        Args:
            db: Database session
            user_id: User ID
            query: Search query
            top_k: Final number of results
            min_score: Minimum score threshold
            source_ids: Filter by sources
            use_reranking: Apply cross-encoder reranking
            use_hybrid: Use BM25+vector hybrid search
            bm25_weight: Weight for BM25 in hybrid (0-1)
        """
        async with create_span("rag.hybrid_retrieve", {"query": query, "top_k": top_k}) as span:
            # Step 1: Get more candidates than needed for reranking
            candidate_k = top_k * 3 if use_reranking else top_k
            
            # Get vector results from pgvector
            vector_results = await self.retrieve(
                db=db,
                user_id=user_id,
                query=query,
                top_k=candidate_k,
                min_score=min_score * 0.5,  # Lower threshold for candidates
                source_ids=source_ids,
            )
            span.set_attribute("vector_results", len(vector_results))
            
            results = vector_results
            
            # Step 2: Hybrid search with BM25
            if use_hybrid and vector_results:
                from app.services.hybrid_search_service import hybrid_search_service
                
                # Build BM25 index from vector results (or cache would be better)
                await hybrid_search_service.build_index(user_id, vector_results)
                
                results = await hybrid_search_service.hybrid_search(
                    user_id=user_id,
                    query=query,
                    vector_results=vector_results,
                    bm25_weight=bm25_weight,
                    top_k=candidate_k,
                )
                span.set_attribute("hybrid_results", len(results))
            
            # Step 3: Reranking
            if use_reranking and results:
                from app.services.reranking_service import reranking_service
                
                results = await reranking_service.rerank(
                    query=query,
                    chunks=results,
                    top_k=top_k,
                )
                span.set_attribute("reranked_results", len(results))
            
            # Step 4: Apply final score threshold and top_k
            final_results = [
                r for r in results[:top_k]
                if r.get("score", 0) >= min_score or r.get("rerank_score", 0) >= min_score
            ]
            
            span.set_attribute("final_results", len(final_results))
            return final_results
    
    async def list_sources(
        self,
        db: AsyncSession,
        user_id: str,
        collection_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all sources accessible to a user:
        - User's own private sources
        - All shared sources (created by any user)
        
        Optionally filter by collection.
        """
        collection_filter = ""
        params = {"user_id": user_id}
        
        if collection_id:
            collection_filter = "AND collection_id = :collection_id"
            params["collection_id"] = collection_id
        
        result = await db.execute(
            text(f"""
                SELECT id, user_id, name, type, visibility, file_size, chunk_count, 
                       metadata, created_at, collection_id, storage_key, storage_type
                FROM rag_sources
                WHERE (user_id = :user_id OR visibility = 'shared')
                {collection_filter}
                ORDER BY visibility ASC, created_at DESC
            """),
            params
        )
        
        return [
            {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "name": row["name"],
                "type": row["type"],
                "visibility": row["visibility"],
                "file_size": row["file_size"],
                "chunk_count": row["chunk_count"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat(),
                "is_owner": str(row["user_id"]) == user_id,
                "collection_id": str(row["collection_id"]) if row["collection_id"] else None,
                "storage_key": row["storage_key"],
                "storage_type": row["storage_type"],
                "has_file": row["storage_key"] is not None,
            }
            for row in result.mappings().all()
        ]
    
    async def download_source(
        self,
        db: AsyncSession,
        source_id: str,
    ) -> Optional[tuple]:
        """
        Download the original file for a source.
        
        Returns:
            Tuple of (file_bytes, filename) or None if no file stored
        """
        result = await db.execute(
            text("""
                SELECT name, storage_key, storage_type
                FROM rag_sources
                WHERE id = :source_id
            """),
            {"source_id": source_id}
        )
        row = result.fetchone()
        
        if not row or not row.storage_key or row.storage_type == "none":
            return None
        
        storage = get_storage_service()
        file_bytes = await storage.download(row.storage_key)
        return (file_bytes, row.name)
    
    async def delete_source(
        self,
        db: AsyncSession,
        user_id: str,
        source_id: str,
    ) -> bool:
        """Delete a source and all its chunks, including from search indices and storage"""
        # Get storage key before deletion
        result = await db.execute(
            text("SELECT storage_key, storage_type FROM rag_sources WHERE id = :id AND user_id = :user_id"),
            {"id": source_id, "user_id": user_id}
        )
        row = result.fetchone()
        
        if not row:
            return False
        
        # Delete from storage if applicable
        if row.storage_key and row.storage_type != "none":
            try:
                storage = get_storage_service()
                await storage.delete(row.storage_key)
            except Exception:
                pass  # File may already be deleted
        
        # Clean up from in-memory indices
        try:
            from app.services.faiss_service import faiss_service
            from app.services.hybrid_search_service import hybrid_search_service
            
            await faiss_service.remove_source(user_id, source_id)
            await hybrid_search_service.remove_source(user_id, source_id)
        except Exception:
            pass  # Indices may not exist
        
        # Delete from database
        result = await db.execute(
            text("""
                DELETE FROM rag_sources
                WHERE id = :source_id AND user_id = :user_id
                RETURNING id
            """),
            {"source_id": source_id, "user_id": user_id}
        )
        await db.commit()
        return result.rowcount > 0
    
    async def update_visibility(
        self,
        db: AsyncSession,
        source_id: str,
        visibility: str,
    ) -> bool:
        """
        Update source visibility (admin only).
        
        Args:
            source_id: The source to update
            visibility: 'private' or 'shared'
            
        Returns:
            True if updated, False if source not found
        """
        result = await db.execute(
            text("""
                UPDATE rag_sources
                SET visibility = :visibility
                WHERE id = :source_id
                RETURNING id
            """),
            {"source_id": source_id, "visibility": visibility}
        )
        await db.commit()
        return result.rowcount > 0
    
    async def get_source(
        self,
        db: AsyncSession,
        source_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a single source by ID"""
        result = await db.execute(
            text("""
                SELECT id, user_id, name, type, visibility, file_size, chunk_count, metadata, created_at
                FROM rag_sources
                WHERE id = :source_id
            """),
            {"source_id": source_id}
        )
        row = result.mappings().fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "name": row["name"],
            "type": row["type"],
            "visibility": row["visibility"],
            "file_size": row["file_size"],
            "chunk_count": row["chunk_count"],
            "metadata": row["metadata"],
            "created_at": row["created_at"].isoformat(),
        }


# Singleton service instance
rag_service = RAGService()


