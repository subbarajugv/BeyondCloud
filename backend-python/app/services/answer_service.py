"""
Answer Service - Context assembly and LLM generation for RAG

Implements:
- Context assembly from retrieved chunks
- LLM answer generation with citations
- Token management
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.tracing import create_span
from app.services.provider_service import provider_service


@dataclass
class AnswerResult:
    """Result from answer generation"""
    answer: str
    citations: List[Dict[str, Any]]
    context_used: str
    chunks_included: int
    model: str
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
        query: str,
        chunks: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
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
            
        Returns:
            AnswerResult with generated answer and metadata
        """
        async with create_span("answer.generate", {"query": query[:100]}) as span:
            # Step 1: Assemble context from chunks
            span.add_event("assembling_context")
            context, included_chunks = self._assemble_context(chunks)
            span.set_attribute("chunks_included", len(included_chunks))
            
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
            
            if response.get("error"):
                return AnswerResult(
                    answer="Sorry, I encountered an error generating the answer.",
                    citations=[],
                    context_used=context,
                    chunks_included=len(included_chunks),
                    model="error",
                    error=response.get("error"),
                )
            
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
            
            span.set_attribute("answer_length", len(response.get("content", "")))
            
            return AnswerResult(
                answer=response.get("content", ""),
                citations=citations,
                context_used=context,
                chunks_included=len(included_chunks),
                model=response.get("model", "unknown"),
            )
    
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
    
    async def answer_with_grounding_check(
        self,
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
        
        return await self.generate_answer(query, grounded_chunks)


# Singleton instance
answer_service = AnswerService()
