"""
Advanced RAG Service - Hybrid retrieval and context optimization pipeline
"""
import asyncio
import logging
import math
from typing import List, Dict, Any, Optional
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from app.tracing import create_span
from app.services.rag_service import rag_service
from app.services.reranking_service import reranking_service
from app.services.provider_service import provider_service
from app.config import get_settings

logger = logging.getLogger(__name__)

class AdvancedRAGService:
    """
    Orchestrates the Advanced RAG pipeline:
    1. Broad Retrieval (Vector Search)
    2. Precision Re-ranking (Cross-Encoder)
    3. Token Budgeting
    4. Hybrid Partitioning (Verbatim vs Summary)
    5. Parallel Summarization
    6. Context Assembly (Lost-in-the-Middle)
    """

    def __init__(self):
        # Default settings
        self.default_context_window = 4096
        self.system_prompt_tokens = 200  # Reserve for system prompt
        self.output_tokens = 1000        # Reserve for answer generation
        self.safety_margin = 100
        
        # Tokenizer cache
        self._tokenizer = None

    def _get_tokenizer(self):
        if self._tokenizer is None:
            try:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback to p50k_base if cl100k not found
                self._tokenizer = tiktoken.get_encoding("p50k_base")
        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        if not text:
            return 0
        try:
            enc = self._get_tokenizer()
            return len(enc.encode(text))
        except Exception:
            # Fallback estimation
            return len(text) // 4

    async def summarize_chunks(self, chunks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Summarize multiple chunks in parallel using LLM
        """
        async def _summarize_one(chunk: Dict[str, Any]) -> Dict[str, Any]:
            content = chunk.get("content", "")
            # Skip short chunks
            if len(content) < 300:
                return {**chunk, "summary": content, "is_summarized": False}
                
            prompt = f"""Summarize the following text efficiently, extracting only key facts relevant to the query: "{query}".
            Keep it under 50 words.

            TEXT:
            {content[:2000]}"""

            try:
                # Use a fast/cheap model if configured, else default
                resp = await provider_service.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.0
                )
                summary = resp.get("content", "").strip()
                return {**chunk, "summary": summary, "is_summarized": True}
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                return {**chunk, "summary": content[:500] + "...", "is_summarized": True, "error": str(e)}

        # Run in parallel
        return await asyncio.gather(*[_summarize_one(c) for c in chunks])

    async def retrieve_advanced(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        context_window: int = 4096,
        hybrid_ratio: float = 0.7,  # 70% verbatim, 30% summary
        source_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full Advanced RAG pipeline
        """
        async with create_span("rag.advanced_retrieve", {"query": query}) as span:
            
            # 1. Broad Retrieval
            # Fetch 50 candidates (10x normal) to cast a wide net
            candidates = await rag_service.retrieve(
                db, user_id, query, top_k=50, min_score=0.3, source_ids=source_ids
            )
            span.set_attribute("candidates_found", len(candidates))
            
            if not candidates:
                return {"context": "", "chunks": []}

            # 2. Precision Re-ranking (Cross-Encoder)
            ranked_chunks = await reranking_service.rerank(
                query, candidates
            )
            
            # 3. Token Budgeting
            query_tokens = self.count_tokens(query)
            available_tokens = context_window - self.system_prompt_tokens - self.output_tokens - query_tokens - self.safety_margin
            
            if available_tokens <= 0:
                # Fallback: Just return top 1
                return {"context": ranked_chunks[0]["content"], "chunks": [ranked_chunks[0]]}

            verbatim_budget = int(available_tokens * hybrid_ratio)
            summary_budget = available_tokens - verbatim_budget
            
            # 4. Hybrid Partitioning
            top_tier = []
            mid_tier = []
            
            current_verbatim_cost = 0
            
            # Assign to tiers
            idx = 0
            while idx < len(ranked_chunks):
                chunk = ranked_chunks[idx]
                tokens = self.count_tokens(chunk["content"]) + 20 # +20 for metadata overhead
                
                if current_verbatim_cost + tokens <= verbatim_budget:
                    top_tier.append(chunk)
                    current_verbatim_cost += tokens
                else:
                    # Overflow -> Check summary budget
                    # Assume summary is ~50 tokens
                    if len(mid_tier) * 50 < summary_budget:
                        mid_tier.append(chunk)
                    else:
                        # Drop remaining
                        break
                idx += 1
            
            span.set_attribute("top_tier_count", len(top_tier))
            span.set_attribute("mid_tier_count", len(mid_tier))

            # 5. Summarization (Mid-Tier)
            if mid_tier:
                span.add_event("summarizing_mid_tier")
                mid_tier = await self.summarize_chunks(mid_tier, query)

            # 6. Context Assembly (Lost-in-the-Middle)
            # Strategy:
            # - Start: Most relevant verbatim (Top 1-2)
            # - Middle: Summaries (Mid Tier) + Lower Verbatim
            # - End: High relevant verbatim (Top Tier remainder)
            
            # Split Top Tier into Start/End
            # If we have [1, 2, 3, 4, 5]
            # Start: [1, 2]
            # End: [3, 4, 5]
            # Middle: [Summaries]
            
            # Ordering: Start -> Middle -> End
            
            split_idx = math.ceil(len(top_tier) / 2) # Split roughly half-half? or bias start?
            # Lost-in-Middle suggests best at START and END.
            # Let's put Top 1 at Start, Top 2 at End. Top 3 at Start... 
            # Re-sort Top Tier into explicit curve: [1, 3, 5 ... 6, 4, 2]
            if len(top_tier) > 2:
                # Simple split: First half at start, Second half at end (but reverse second half so best is at very end?)
                # Actually, standard research says: High ... Low ... High
                
                # Let's do:
                # Start: Top 33%
                # End: Next 33%
                # Mid: Bottom 33% + Summaries
                
                # Simpler implementation:
                # Start: Top 1
                # End: Top 2
                # Then fill Middle with rest + summaries
                
                start_chunks = [top_tier[0]] if top_tier else []
                end_chunks = [top_tier[1]] if len(top_tier) > 1 else []
                middle_verbatim = top_tier[2:]
            else:
                start_chunks = top_tier
                end_chunks = []
                middle_verbatim = []

            # Assemble text
            context_parts = []
            final_chunks = []
            
            # Start
            for c in start_chunks:
                context_parts.append(f"--- [Source: {c.get('source_name', 'Unknown')}]\n{c['content']}")
                final_chunks.append(c)

            # Middle (Summaries)
            for c in mid_tier:
                context_parts.append(f"--- [Source: {c.get('source_name', 'Unknown')} (Summary)]\n{c['summary']}")
                final_chunks.append(c) # These have 'summary' field now

            # Middle (Verbatim)
            for c in middle_verbatim:
                context_parts.append(f"--- [Source: {c.get('source_name', 'Unknown')}]\n{c['content']}")
                final_chunks.append(c)

            # End
            for c in end_chunks:
                context_parts.append(f"--- [Source: {c.get('source_name', 'Unknown')}]\n{c['content']}")
                final_chunks.append(c)
            
            full_context = "\n\n".join(context_parts)
            
            span.set_attribute("final_context_tokens", self.count_tokens(full_context))

            return {
                "context": full_context,
                "chunks": final_chunks, # Includes summary status
                "tier_breakdown": {
                    "verbatim": len(top_tier),
                    "summarized": len(mid_tier),
                    "original_candidates": len(candidates)
                }
            }

advanced_rag_service = AdvancedRAGService()
