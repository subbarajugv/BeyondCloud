"""
Query Service - Query preprocessing for RAG

Implements:
- Query Rewriting (LLM-based)
- Spelling Correction
- Human-in-the-Loop confirmation

Future Extensions (commented):
- Query Expansion (synonyms)
- Query Decomposition (multi-hop)
- HyDE (Hypothetical Document Embeddings)
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from app.tracing import create_span


class QueryStatus(str, Enum):
    """Status of processed query"""
    READY = "ready"           # Query ready for retrieval
    PENDING_REVIEW = "pending_review"  # Awaiting human confirmation
    MODIFIED = "modified"     # Query was modified
    ORIGINAL = "original"     # No changes made


@dataclass
class ProcessedQuery:
    """Result of query preprocessing"""
    original_query: str
    processed_query: str
    status: QueryStatus
    corrections: List[Dict[str, str]]  # List of {original, corrected, type}
    confidence: float  # 0-1 confidence in modifications
    requires_confirmation: bool
    metadata: Dict[str, Any]


class QueryService:
    """
    Query preprocessing service for customer-facing RAG
    
    Flow:
    1. User submits query
    2. Spelling correction applied
    3. LLM rewrites for better retrieval
    4. If significant changes, ask for human confirmation
    5. Return processed query for retrieval
    """
    
    def __init__(self):
        self._spell_checker = None
        self._llm_client = None
    
    async def get_spell_checker(self):
        """Lazy-load spell checker"""
        if self._spell_checker is None:
            from spellchecker import SpellChecker
            self._spell_checker = SpellChecker()
        return self._spell_checker
    
    async def process_query(
        self,
        query: str,
        context: Optional[str] = None,
        auto_confirm: bool = False,
        rewrite: bool = True,
        spell_check: bool = True,
    ) -> ProcessedQuery:
        """
        Process a user query for optimal retrieval
        
        Args:
            query: Original user query
            context: Optional conversation context
            auto_confirm: If True, skip human confirmation
            rewrite: Enable LLM query rewriting
            spell_check: Enable spelling correction
        
        Returns:
            ProcessedQuery with status and modifications
        """
        async with create_span("query.process", {"query": query[:100]}) as span:
            corrections = []
            processed = query
            confidence = 1.0
            
            # Step 1: Spelling Correction
            if spell_check:
                span.add_event("spell_check")
                processed, spell_corrections = await self._correct_spelling(processed)
                corrections.extend(spell_corrections)
                if spell_corrections:
                    confidence *= 0.9  # Slight confidence reduction
            
            # Step 2: Query Rewriting (LLM)
            if rewrite:
                span.add_event("query_rewrite")
                rewritten, rewrite_info = await self._rewrite_query(processed, context)
                if rewritten != processed:
                    corrections.append({
                        "original": processed,
                        "corrected": rewritten,
                        "type": "rewrite",
                        "reason": rewrite_info.get("reason", "Improved for retrieval"),
                    })
                    processed = rewritten
                    confidence *= rewrite_info.get("confidence", 0.85)
            
            # ================================================================
            # FUTURE: Query Expansion
            # ================================================================
            # Uncomment when implementing synonym/related term expansion:
            #
            # if expand:
            #     span.add_event("query_expand")
            #     processed, expansions = await self._expand_query(processed)
            #     corrections.extend(expansions)
            
            # ================================================================
            # FUTURE: Query Decomposition  
            # ================================================================
            # Uncomment for multi-hop reasoning (complex queries):
            #
            # if decompose:
            #     span.add_event("query_decompose")
            #     sub_queries = await self._decompose_query(processed)
            #     # Return multiple sub-queries for parallel retrieval
            #     metadata["sub_queries"] = sub_queries
            
            # ================================================================
            # FUTURE: HyDE (Hypothetical Document Embeddings)
            # ================================================================
            # Uncomment for improved dense retrieval:
            #
            # if use_hyde:
            #     span.add_event("hyde")
            #     hypothetical_doc = await self._generate_hypothetical_doc(processed)
            #     metadata["hyde_doc"] = hypothetical_doc
            #     # Use hypothetical_doc for embedding instead of query
            
            # Determine if human confirmation needed
            requires_confirmation = self._needs_confirmation(
                original=query,
                processed=processed,
                corrections=corrections,
                confidence=confidence,
                auto_confirm=auto_confirm,
            )
            
            status = QueryStatus.ORIGINAL
            if corrections:
                status = QueryStatus.PENDING_REVIEW if requires_confirmation else QueryStatus.MODIFIED
            if not requires_confirmation:
                status = QueryStatus.READY if corrections else QueryStatus.ORIGINAL
            
            span.set_attribute("status", status.value)
            span.set_attribute("correction_count", len(corrections))
            
            return ProcessedQuery(
                original_query=query,
                processed_query=processed,
                status=status,
                corrections=corrections,
                confidence=confidence,
                requires_confirmation=requires_confirmation,
                metadata={
                    "rewrite_enabled": rewrite,
                    "spell_check_enabled": spell_check,
                },
            )
    
    async def _correct_spelling(self, query: str) -> tuple[str, List[Dict[str, str]]]:
        """
        Correct spelling errors in query
        
        Returns:
            Tuple of (corrected_query, list_of_corrections)
        """
        spell = await self.get_spell_checker()
        words = query.split()
        corrections = []
        corrected_words = []
        
        for word in words:
            # Skip short words, numbers, special chars
            clean_word = ''.join(c for c in word if c.isalpha())
            if len(clean_word) < 3 or not clean_word:
                corrected_words.append(word)
                continue
            
            # Check if misspelled
            if clean_word.lower() not in spell:
                correction = spell.correction(clean_word.lower())
                if correction and correction != clean_word.lower():
                    # Preserve original casing pattern
                    if clean_word.isupper():
                        correction = correction.upper()
                    elif clean_word[0].isupper():
                        correction = correction.capitalize()
                    
                    # Replace in original word (preserve punctuation)
                    corrected_word = word.replace(clean_word, correction)
                    corrected_words.append(corrected_word)
                    corrections.append({
                        "original": word,
                        "corrected": corrected_word,
                        "type": "spelling",
                    })
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return " ".join(corrected_words), corrections
    
    async def _rewrite_query(
        self, 
        query: str, 
        context: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Use LLM to rewrite query for better retrieval
        
        Returns:
            Tuple of (rewritten_query, info_dict)
        """
        from app.services.provider_service import provider_service
        
        system_prompt = """You are a query optimizer for a document retrieval system.
Your task is to rewrite user queries to improve search results.

Rules:
1. Expand abbreviations and acronyms
2. Add context from the conversation if helpful
3. Convert questions to descriptive statements
4. Keep the core intent unchanged
5. Be concise but comprehensive

Respond with ONLY the rewritten query, nothing else.
If the query is already optimal, respond with the exact same query."""

        user_prompt = f"Query: {query}"
        if context:
            user_prompt = f"Context: {context}\n\n{user_prompt}"
        
        try:
            # Use default provider for rewriting
            response = await provider_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=None,  # Use default
                temperature=0.3,  # Low temperature for consistency
                max_tokens=200,
            )
            
            rewritten = response.get("content", query).strip()
            
            # Basic validation - don't accept dramatically different lengths
            len_ratio = len(rewritten) / len(query) if query else 1
            if 0.3 < len_ratio < 5.0:
                return rewritten, {
                    "confidence": 0.85,
                    "reason": "LLM optimization",
                }
            else:
                return query, {"confidence": 1.0, "reason": "Rewrite rejected (length)"}
                
        except Exception as e:
            # Fallback to original on error
            return query, {"confidence": 1.0, "reason": f"LLM error: {str(e)}"}
    
    def _needs_confirmation(
        self,
        original: str,
        processed: str,
        corrections: List[Dict[str, str]],
        confidence: float,
        auto_confirm: bool,
    ) -> bool:
        """
        Determine if human confirmation is needed
        
        Confirmation required when:
        - Significant changes were made
        - Confidence is low
        - Not in auto-confirm mode
        """
        if auto_confirm:
            return False
        
        # No changes = no confirmation needed
        if original == processed:
            return False
        
        # Low confidence = needs confirmation
        if confidence < 0.7:
            return True
        
        # Many corrections = needs confirmation
        if len(corrections) > 2:
            return True
        
        # Significant length change = needs confirmation
        len_change = abs(len(processed) - len(original)) / len(original) if original else 0
        if len_change > 0.5:  # More than 50% length change
            return True
        
        return False
    
    async def confirm_query(
        self,
        query_id: str,
        confirmed: bool,
        user_modified_query: Optional[str] = None,
    ) -> ProcessedQuery:
        """
        Human confirms or modifies the processed query
        
        Args:
            query_id: ID of the pending query
            confirmed: User accepts the modification
            user_modified_query: Optional user-provided alternative
        
        Returns:
            Updated ProcessedQuery ready for retrieval
        """
        # In a full implementation, this would:
        # 1. Look up the pending query by ID
        # 2. Update status based on user action
        # 3. Store user preference for learning
        
        # For now, we return a simple confirmation
        if user_modified_query:
            return ProcessedQuery(
                original_query="",  # Would come from stored state
                processed_query=user_modified_query,
                status=QueryStatus.READY,
                corrections=[{"type": "user_override", "corrected": user_modified_query}],
                confidence=1.0,  # User is always right
                requires_confirmation=False,
                metadata={"source": "user_modification"},
            )
        elif confirmed:
            return ProcessedQuery(
                original_query="",
                processed_query="",  # Would come from stored state
                status=QueryStatus.READY,
                corrections=[],
                confidence=1.0,
                requires_confirmation=False,
                metadata={"source": "user_confirmed"},
            )
        else:
            # User rejected - use original
            return ProcessedQuery(
                original_query="",
                processed_query="",  # Would use original
                status=QueryStatus.READY,
                corrections=[],
                confidence=1.0,
                requires_confirmation=False,
                metadata={"source": "user_rejected"},
            )

    # ========================================================================
    # FUTURE IMPLEMENTATIONS (Placeholder methods)
    # ========================================================================
    
    # async def _expand_query(self, query: str) -> tuple[str, List[Dict[str, str]]]:
    #     """
    #     FUTURE: Expand query with synonyms and related terms
    #     
    #     Implementation options:
    #     1. WordNet for synonyms
    #     2. Domain-specific thesaurus
    #     3. Embedding-based similarity
    #     
    #     Example:
    #         "auth errors" -> "authentication authorization errors failures issues"
    #     """
    #     pass
    
    # async def _decompose_query(self, query: str) -> List[str]:
    #     """
    #     FUTURE: Break complex queries into sub-queries
    #     
    #     Useful for multi-hop reasoning:
    #         "How does auth differ between v1 and v2?"
    #         -> ["How does auth work in v1?", "How does auth work in v2?"]
    #     
    #     Then merge results from both retrievals.
    #     """
    #     pass
    
    # async def _generate_hypothetical_doc(self, query: str) -> str:
    #     """
    #     FUTURE: HyDE - Generate hypothetical document for embedding
    #     
    #     Instead of embedding the query, generate what an ideal
    #     answer document would look like, then embed that.
    #     
    #     This bridges the query-document semantic gap.
    #     
    #     Paper: https://arxiv.org/abs/2212.10496
    #     """
    #     pass


# Singleton service instance
query_service = QueryService()
