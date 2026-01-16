"""
Reranking Service - Cross-encoder based reranking for improved precision

Uses a cross-encoder model to score query-document pairs directly,
providing more accurate relevance scores than bi-encoder embeddings.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.tracing import create_span


@dataclass
class RankedChunk:
    """Chunk with reranking score"""
    chunk: Dict[str, Any]
    original_score: float
    rerank_score: float


class RerankingService:
    """
    Cross-encoder based reranking
    
    Improves retrieval precision by scoring query-document pairs
    directly rather than comparing embeddings.
    """
    
    def __init__(self):
        self._model = None
        self._model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    async def get_model(self):
        """Lazy-load the cross-encoder model"""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self._model_name)
        return self._model
    
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks using cross-encoder
        
        Args:
            query: Search query
            chunks: Retrieved chunks with 'content' field
            top_k: Return only top-k after reranking (None = all)
            
        Returns:
            Reranked chunks with updated scores
        """
        if not chunks:
            return []
        
        async with create_span("rerank", {"query": query[:100], "chunk_count": len(chunks)}) as span:
            model = await self.get_model()
            
            # Prepare query-document pairs
            pairs = [(query, chunk.get("content", "")) for chunk in chunks]
            
            # Score all pairs
            span.add_event("scoring")
            scores = model.predict(pairs)
            
            # Combine with original data and sort
            ranked = []
            for chunk, rerank_score in zip(chunks, scores):
                ranked_chunk = {
                    **chunk,
                    "original_score": chunk.get("score", 0),
                    "rerank_score": float(rerank_score),
                    "score": float(rerank_score),  # Use rerank score as primary
                }
                ranked.append(ranked_chunk)
            
            # Sort by rerank score descending
            ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # Apply top-k if specified
            if top_k is not None:
                ranked = ranked[:top_k]
            
            span.set_attribute("result_count", len(ranked))
            return ranked
    
    async def rerank_with_threshold(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        min_score: float = 0.0,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank and filter by minimum rerank score
        
        Args:
            query: Search query
            chunks: Retrieved chunks
            min_score: Minimum rerank score to include
            top_k: Max results to return
            
        Returns:
            Filtered and reranked chunks
        """
        ranked = await self.rerank(query, chunks, top_k=None)
        
        # Filter by threshold
        filtered = [c for c in ranked if c["rerank_score"] >= min_score]
        
        # Apply top-k
        if top_k is not None:
            filtered = filtered[:top_k]
        
        return filtered


# Singleton instance
reranking_service = RerankingService()
