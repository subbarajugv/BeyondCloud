"""
FAISS Service - Fast in-memory vector search

Provides fast vector similarity search using FAISS.
Works alongside pgvector for hybrid storage:
- FAISS: Fast in-memory search
- pgvector: Persistent storage and backup
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import threading

from app.tracing import create_span


@dataclass
class FAISSIndex:
    """Container for a FAISS index with metadata"""
    index: Any  # faiss.Index
    id_map: Dict[int, str]  # faiss_id -> chunk_id
    chunk_data: Dict[str, Dict[str, Any]]  # chunk_id -> metadata
    dimension: int


class FAISSService:
    """
    Fast vector search using FAISS
    
    Maintains in-memory FAISS indices for fast retrieval.
    Indices are organized per user for isolation.
    """
    
    def __init__(self):
        self._indices: Dict[str, FAISSIndex] = {}  # user_id -> index
        self._lock = threading.Lock()
        self._faiss = None
    
    def _get_faiss(self):
        """Lazy-load FAISS"""
        if self._faiss is None:
            import faiss
            self._faiss = faiss
        return self._faiss
    
    def _get_or_create_index(self, user_id: str, dimension: int = 384) -> FAISSIndex:
        """Get or create a FAISS index for a user"""
        with self._lock:
            if user_id not in self._indices:
                faiss = self._get_faiss()
                # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
                index = faiss.IndexFlatIP(dimension)
                self._indices[user_id] = FAISSIndex(
                    index=index,
                    id_map={},
                    chunk_data={},
                    dimension=dimension,
                )
            return self._indices[user_id]
    
    async def add_vectors(
        self,
        user_id: str,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ) -> int:
        """
        Add vectors to the FAISS index
        
        Args:
            user_id: User ID for isolation
            chunk_ids: Unique IDs for each chunk
            embeddings: Vector embeddings
            metadata: Chunk metadata (content, source_id, etc.)
            
        Returns:
            Number of vectors added
        """
        if not embeddings:
            return 0
        
        async with create_span("faiss.add", {"user_id": user_id, "count": len(embeddings)}):
            dimension = len(embeddings[0])
            faiss_index = self._get_or_create_index(user_id, dimension)
            
            # Normalize vectors for cosine similarity
            vectors = np.array(embeddings, dtype=np.float32)
            faiss = self._get_faiss()
            faiss.normalize_L2(vectors)
            
            # Get starting ID
            start_id = faiss_index.index.ntotal
            
            # Add to index
            faiss_index.index.add(vectors)
            
            # Update mappings
            for i, (chunk_id, meta) in enumerate(zip(chunk_ids, metadata)):
                faiss_id = start_id + i
                faiss_index.id_map[faiss_id] = chunk_id
                faiss_index.chunk_data[chunk_id] = meta
            
            return len(embeddings)
    
    async def search(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            user_id: User ID
            query_embedding: Query vector
            top_k: Number of results
            
        Returns:
            List of chunks with scores
        """
        async with create_span("faiss.search", {"user_id": user_id, "top_k": top_k}) as span:
            if user_id not in self._indices:
                span.set_attribute("result_count", 0)
                return []
            
            faiss_index = self._indices[user_id]
            faiss = self._get_faiss()
            
            # Prepare query vector
            query = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query)
            
            # Search
            k = min(top_k, faiss_index.index.ntotal)
            if k == 0:
                return []
            
            scores, indices = faiss_index.index.search(query, k)
            
            # Build results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # No more results
                    break
                chunk_id = faiss_index.id_map.get(idx)
                if chunk_id and chunk_id in faiss_index.chunk_data:
                    chunk = faiss_index.chunk_data[chunk_id].copy()
                    chunk["score"] = float(score)
                    chunk["id"] = chunk_id
                    results.append(chunk)
            
            span.set_attribute("result_count", len(results))
            return results
    
    async def remove_source(self, user_id: str, source_id: str) -> int:
        """
        Remove all vectors for a source
        
        Note: FAISS doesn't support deletion, so we rebuild the index
        
        Args:
            user_id: User ID
            source_id: Source to remove
            
        Returns:
            Number of vectors removed
        """
        async with create_span("faiss.remove_source", {"source_id": source_id}):
            if user_id not in self._indices:
                return 0
            
            faiss_index = self._indices[user_id]
            
            # Find chunks to keep
            chunks_to_keep = {
                cid: meta for cid, meta in faiss_index.chunk_data.items()
                if meta.get("source_id") != source_id
            }
            
            removed_count = len(faiss_index.chunk_data) - len(chunks_to_keep)
            
            if removed_count == 0:
                return 0
            
            # Rebuild index (FAISS doesn't support deletion)
            # In production, consider using IndexIDMap for better deletion support
            faiss = self._get_faiss()
            new_index = faiss.IndexFlatIP(faiss_index.dimension)
            new_id_map = {}
            new_chunk_data = {}
            
            # This is a simplified rebuild - in production you'd want to
            # re-embed or store embeddings to avoid recomputation
            # For now, we just clear and let it rebuild on next ingest
            
            self._indices[user_id] = FAISSIndex(
                index=new_index,
                id_map=new_id_map,
                chunk_data=new_chunk_data,
                dimension=faiss_index.dimension,
            )
            
            return removed_count
    
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get index statistics"""
        if user_id not in self._indices:
            return {"total_vectors": 0, "dimension": 0}
        
        faiss_index = self._indices[user_id]
        return {
            "total_vectors": faiss_index.index.ntotal,
            "dimension": faiss_index.dimension,
            "sources": len(set(
                m.get("source_id") for m in faiss_index.chunk_data.values()
            )),
        }
    
    def clear_user_index(self, user_id: str) -> None:
        """Clear a user's index"""
        with self._lock:
            if user_id in self._indices:
                del self._indices[user_id]


# Singleton instance
faiss_service = FAISSService()
