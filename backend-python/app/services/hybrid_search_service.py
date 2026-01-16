"""
Hybrid Search Service - Combines BM25 keyword search with vector search

Implements Reciprocal Rank Fusion (RRF) to merge results from
multiple search methods for improved retrieval quality.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import threading

from rank_bm25 import BM25Okapi

from app.tracing import create_span


@dataclass
class BM25Index:
    """Container for BM25 index with metadata"""
    bm25: BM25Okapi
    documents: List[str]  # Tokenized docs for reference
    chunk_ids: List[str]
    chunk_data: Dict[str, Dict[str, Any]]


class HybridSearchService:
    """
    Hybrid search combining BM25 and vector similarity
    
    Uses Reciprocal Rank Fusion (RRF) to merge results from:
    1. BM25 keyword search (lexical matching)
    2. Vector similarity search (semantic matching)
    """
    
    def __init__(self):
        self._indices: Dict[str, BM25Index] = {}  # user_id -> index
        self._lock = threading.Lock()
        self.rrf_k = 60  # RRF parameter (typically 60)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        # Basic tokenization - in production use proper tokenizer
        import re
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    async def build_index(
        self,
        user_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """
        Build or rebuild BM25 index from chunks
        
        Args:
            user_id: User ID for isolation
            chunks: List of chunks with 'id' and 'content'
            
        Returns:
            Number of documents indexed
        """
        if not chunks:
            return 0
        
        async with create_span("hybrid.build_index", {"user_id": user_id, "count": len(chunks)}):
            # Tokenize all documents
            tokenized = [self._tokenize(c.get("content", "")) for c in chunks]
            chunk_ids = [c.get("id", str(i)) for i, c in enumerate(chunks)]
            chunk_data = {c.get("id", str(i)): c for i, c in enumerate(chunks)}
            
            # Build BM25 index
            bm25 = BM25Okapi(tokenized)
            
            with self._lock:
                self._indices[user_id] = BM25Index(
                    bm25=bm25,
                    documents=tokenized,
                    chunk_ids=chunk_ids,
                    chunk_data=chunk_data,
                )
            
            return len(chunks)
    
    async def add_to_index(
        self,
        user_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """
        Add chunks to existing BM25 index
        
        Note: BM25Okapi doesn't support incremental updates,
        so we rebuild the entire index. For large indices,
        consider using a more sophisticated approach.
        """
        if user_id not in self._indices:
            return await self.build_index(user_id, chunks)
        
        # Get existing chunks and add new ones
        existing = self._indices[user_id]
        all_chunks = list(existing.chunk_data.values()) + chunks
        
        return await self.build_index(user_id, all_chunks)
    
    async def bm25_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        BM25 keyword search
        
        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results
            
        Returns:
            Chunks with BM25 scores
        """
        async with create_span("hybrid.bm25_search", {"query": query[:100]}) as span:
            if user_id not in self._indices:
                return []
            
            index = self._indices[user_id]
            query_tokens = self._tokenize(query)
            
            # Get BM25 scores for all documents
            scores = index.bm25.get_scores(query_tokens)
            
            # Get top-k indices
            import numpy as np
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include positive scores
                    chunk_id = index.chunk_ids[idx]
                    chunk = index.chunk_data[chunk_id].copy()
                    chunk["bm25_score"] = float(scores[idx])
                    chunk["score"] = float(scores[idx])
                    results.append(chunk)
            
            span.set_attribute("result_count", len(results))
            return results
    
    async def hybrid_search(
        self,
        user_id: str,
        query: str,
        vector_results: List[Dict[str, Any]],
        bm25_weight: float = 0.5,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion
        
        Args:
            user_id: User ID
            query: Search query
            vector_results: Results from vector search
            bm25_weight: Weight for BM25 (0-1), vector gets 1-bm25_weight
            top_k: Number of results
            
        Returns:
            Merged and ranked results
        """
        async with create_span("hybrid.search", {"query": query[:100]}) as span:
            # Get BM25 results
            bm25_results = await self.bm25_search(user_id, query, top_k=top_k * 2)
            
            # Compute RRF scores
            rrf_scores: Dict[str, float] = {}
            chunk_data: Dict[str, Dict[str, Any]] = {}
            
            # Score from BM25 results
            for rank, chunk in enumerate(bm25_results):
                chunk_id = chunk.get("id", "")
                rrf_score = bm25_weight * (1.0 / (self.rrf_k + rank + 1))
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf_score
                chunk_data[chunk_id] = chunk
            
            # Score from vector results
            vector_weight = 1.0 - bm25_weight
            for rank, chunk in enumerate(vector_results):
                chunk_id = chunk.get("id", "")
                rrf_score = vector_weight * (1.0 / (self.rrf_k + rank + 1))
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf_score
                if chunk_id not in chunk_data:
                    chunk_data[chunk_id] = chunk
            
            # Sort by RRF score
            sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
            
            results = []
            for chunk_id in sorted_ids[:top_k]:
                chunk = chunk_data[chunk_id].copy()
                chunk["rrf_score"] = rrf_scores[chunk_id]
                chunk["score"] = rrf_scores[chunk_id]
                results.append(chunk)
            
            span.set_attribute("result_count", len(results))
            span.set_attribute("bm25_count", len(bm25_results))
            span.set_attribute("vector_count", len(vector_results))
            
            return results
    
    async def remove_source(self, user_id: str, source_id: str) -> int:
        """Remove all documents for a source from the BM25 index"""
        if user_id not in self._indices:
            return 0
        
        index = self._indices[user_id]
        
        # Filter out chunks from the source
        remaining = [
            index.chunk_data[cid]
            for cid in index.chunk_ids
            if index.chunk_data[cid].get("source_id") != source_id
        ]
        
        removed = len(index.chunk_ids) - len(remaining)
        
        if removed > 0:
            await self.build_index(user_id, remaining)
        
        return removed


# Singleton instance
hybrid_search_service = HybridSearchService()
