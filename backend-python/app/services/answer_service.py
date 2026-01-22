"""
Answer Service - Context assembly and LLM generation for RAG

Implements:
- Context assembly from retrieved chunks with configurable ordering
- LLM answer generation with citations
- Token management
- Hallucination detection
"""
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum

from app.tracing import create_span
from app.services.provider_service import provider_service
from app.services.usage_service import usage_service
from sqlalchemy.ext.asyncio import AsyncSession


class ContextOrdering(str, Enum):
    SCORE_DESC = "score_desc"    # Highest score first (default)
    SCORE_ASC = "score_asc"      # Lowest score first
    POSITION = "position"         # Original document position


@dataclass
class AnswerResult:
    """Result from answer generation"""
    answer: str
    citations: List[Dict[str, Any]]
    context_used: str
    chunks_included: int
    model: str
    grounding_score: float = 1.0
    hallucination_check: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnswerService:
    """
    RAG Answer Generation Service
    
    Takes retrieved chunks and generates an answer using LLM.
    """
    
    # Default system prompt for RAG answering
    DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

Rules:
1. Only use information from the provided context to answer
2. If the context doesn't contain enough information, say so
3. Cite your sources by mentioning the document name when relevant
4. Be concise but thorough
5. If you're uncertain, express your uncertainty

Context will be provided in the following format:
---
[Source: document_name]
content
---"""

    def __init__(self):
        self.max_context_chars = 8000  # Rough estimate, ~2000 tokens
    
    async def generate_answer(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        context_ordering: ContextOrdering = ContextOrdering.SCORE_DESC,
        check_hallucination: bool = False,
    ) -> AnswerResult:
        """
        Generate an answer from retrieved chunks
        
        Args:
            query: User's question
            chunks: Retrieved chunks from RAG service
            system_prompt: Custom system prompt (or default)
            model: LLM model to use
            temperature: Sampling temperature (low for factual answers)
            max_tokens: Max tokens in response
            context_ordering: How to order chunks in context
            check_hallucination: Run hallucination detection on answer
            
        Returns:
            AnswerResult with generated answer and metadata
        """
        async with create_span("answer.generate", {"query": query[:100]}) as span:
            # Step 1: Order and assemble context from chunks
            span.add_event("assembling_context")
            ordered_chunks = self._order_chunks(chunks, context_ordering)
            context, included_chunks = self._assemble_context(ordered_chunks)
            span.set_attribute("chunks_included", len(included_chunks))
            span.set_attribute("ordering", context_ordering.value)
            
            if not included_chunks:
                return AnswerResult(
                    answer="I couldn't find any relevant information to answer your question.",
                    citations=[],
                    context_used="",
                    chunks_included=0,
                    model="none",
                    error="No relevant context available",
                )
            
            # Step 2: Build messages for LLM
            system = system_prompt or self.DEFAULT_SYSTEM_PROMPT
            user_message = f"""Context:
{context}

Question: {query}

Please answer based on the context above."""

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ]
            
            # Step 3: Call LLM
            span.add_event("calling_llm")
            response = await provider_service.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Tracking: Increment LLM request and tokens
            await usage_service.increment(db, user_id, "llm_requests")
            usage = response.get("usage", {})
            if usage.get("prompt_tokens"):
                await usage_service.increment(db, user_id, "llm_tokens_input", amount=usage["prompt_tokens"])
            if usage.get("completion_tokens"):
                await usage_service.increment(db, user_id, "llm_tokens_output", amount=usage["completion_tokens"])
            
            if response.get("error"):
                return AnswerResult(
                    answer="Sorry, I encountered an error generating the answer.",
                    citations=[],
                    context_used=context,
                    chunks_included=len(included_chunks),
                    model="error",
                    error=response.get("error"),
                )
            
            answer_text = response.get("content", "")
            
            # Build citations from included chunks
            citations = [
                {
                    "source_id": str(c.get("source_id", "")),
                    "source_name": c.get("source_name", "Unknown"),
                    "score": c.get("score", 0),
                    "content_preview": c.get("content", "")[:100] + "...",
                }
                for c in included_chunks
            ]
            
            # Step 4: Hallucination check (if enabled)
            hallucination_result = None
            grounding_score = 1.0
            
            if check_hallucination:
                span.add_event("checking_hallucination")
                hallucination_result = await self._check_hallucination(
                    query=query,
                    answer=answer_text,
                    context=context,
                    db=db,
                    user_id=user_id,
                )
                grounding_score = hallucination_result.get("grounding_score", 1.0)
                span.set_attribute("grounding_score", grounding_score)
            
            span.set_attribute("answer_length", len(answer_text))
            
            return AnswerResult(
                answer=answer_text,
                citations=citations,
                context_used=context,
                chunks_included=len(included_chunks),
                model=response.get("model", "unknown"),
                grounding_score=grounding_score,
                hallucination_check=hallucination_result,
            )
    
    def _order_chunks(
        self,
        chunks: List[Dict[str, Any]],
        ordering: ContextOrdering,
    ) -> List[Dict[str, Any]]:
        """Order chunks according to specified strategy"""
        if ordering == ContextOrdering.SCORE_DESC:
            return sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)
        elif ordering == ContextOrdering.SCORE_ASC:
            return sorted(chunks, key=lambda c: c.get("score", 0))
        elif ordering == ContextOrdering.POSITION:
            # Order by chunk_index if available, otherwise preserve order
            return sorted(chunks, key=lambda c: c.get("metadata", {}).get("chunk_index", 0))
        return chunks
    
    def _assemble_context(
        self, 
        chunks: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Assemble context string from chunks, respecting token limits
        
        Returns:
            Tuple of (context_string, included_chunks)
        """
        context_parts = []
        included_chunks = []
        current_length = 0
        
        for chunk in chunks:
            content = chunk.get("content", "")
            source_name = chunk.get("source_name", "Unknown")
            
            # Format chunk with source attribution
            formatted = f"""---
[Source: {source_name}]
{content}
---"""
            
            # Check if we can fit this chunk
            if current_length + len(formatted) > self.max_context_chars:
                break
            
            context_parts.append(formatted)
            included_chunks.append(chunk)
            current_length += len(formatted)
        
        return "\n\n".join(context_parts), included_chunks
    
    async def _check_hallucination(
        self,
        query: str,
        answer: str,
        context: str,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        LLM-based hallucination detection
        
        Analyzes if the answer is grounded in the provided context.
        
        Args:
            query: The user's question
            answer: The generated answer to check
            context: The context used to generate the answer
            db: Database session for usage tracking (optional)
            user_id: User ID for usage tracking (optional)
        
        Returns:
            Dict with grounding_score (0-1), issues, and explanation
        """
        async with create_span("answer.hallucination_check") as span:
            prompt = f"""You are a fact-checker. Analyze if the ANSWER is fully grounded in the CONTEXT.

CONTEXT:
{context[:4000]}

QUESTION: {query}

ANSWER: {answer}

Analyze the answer and respond with JSON:
{{
    "grounding_score": 0.0-1.0,  // 1.0 = fully grounded, 0.0 = hallucinated
    "issues": ["list of claims not in context"],
    "verdict": "grounded" | "partially_grounded" | "hallucinated",
    "explanation": "brief explanation"
}}"""

            try:
                response = await provider_service.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )
                
                # Track hallucination check LLM usage if db and user_id provided
                if db and user_id:
                    await usage_service.increment(db, user_id, "llm_requests")
                    usage = response.get("usage", {})
                    if usage.get("prompt_tokens"):
                        await usage_service.increment(db, user_id, "llm_tokens_input", amount=usage["prompt_tokens"])
                    if usage.get("completion_tokens"):
                        await usage_service.increment(db, user_id, "llm_tokens_output", amount=usage["completion_tokens"])
                
                import json
                content = response.get("content", "").strip()
                
                # Extract JSON from response
                if "{" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                    result = json.loads(json_str)
                    span.set_attribute("verdict", result.get("verdict", "unknown"))
                    return result
                
                return {"grounding_score": 0.5, "verdict": "unknown", "issues": [], "explanation": "Could not parse result"}
                
            except Exception as e:
                span.set_attribute("error", str(e))
                return {"grounding_score": 0.5, "verdict": "error", "issues": [], "explanation": str(e)}
    
    async def answer_with_grounding_check(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        chunks: List[Dict[str, Any]],
        min_grounding_score: float = 0.5,
    ) -> AnswerResult:
        """
        Generate answer only if grounding is sufficient
        
        This is a simplified grounding check - just ensures
        we have chunks with decent relevance scores.
        
        Future: Implement proper grounding verification with LLM
        """
        # Filter chunks by minimum score
        grounded_chunks = [
            c for c in chunks 
            if c.get("score", 0) >= min_grounding_score
        ]
        
        if not grounded_chunks:
            return AnswerResult(
                answer="I don't have enough relevant information to answer this question confidently.",
                citations=[],
                context_used="",
                chunks_included=0,
                model="none",
                error="Insufficient grounding",
            )
        
        return await self.generate_answer(db, user_id, query, grounded_chunks, check_hallucination=True)


# Singleton instance
answer_service = AnswerService()

