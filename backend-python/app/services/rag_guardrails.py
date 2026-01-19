"""
RAG Guardrails - Input/Output validation for RAG queries

Provides:
- Pre-query validation (PII, toxicity, injection)
- Post-generation validation (hallucination, harmful content)
"""
import re
from typing import Tuple, Optional, List
from app.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# Input Validation Patterns
# =============================================================================

# PII patterns (simplified - production should use libraries like presidio)
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}

PII_COMPILED = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in PII_PATTERNS.items()}

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(?:previous|prior|above)\s+instructions",
    r"disregard\s+(?:previous|prior|above)\s+instructions",
    r"forget\s+(?:everything|all)\s+(?:you|I)\s+(?:said|told)",
    r"you\s+are\s+now\s+(?:a|an)",
    r"pretend\s+(?:you|to\s+be)",
    r"act\s+as\s+(?:if|a|an)",
    r"new\s+instruction[s]?:",
    r"system\s*:\s*",
    r"\[INST\]",
    r"<\|(?:system|user|assistant)\|>",
]

INJECTION_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS]

# Toxic/harmful query patterns
TOXICITY_PATTERNS = [
    r"how\s+to\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|weapon|explosive)",
    r"how\s+to\s+(?:kill|murder|harm)\s+(?:someone|people)",
    r"how\s+to\s+(?:hack|break\s+into)",
    r"illegal\s+(?:drugs|weapons)",
    r"child\s+(?:abuse|exploitation|pornography)",
]

TOXICITY_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in TOXICITY_PATTERNS]


# =============================================================================
# Query Validation
# =============================================================================

def validate_query(query: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Validate a RAG query for safety.
    
    Returns:
        (is_valid, block_reason, warnings)
        - is_valid: True if query can proceed
        - block_reason: If blocked, the reason
        - warnings: Non-blocking issues (e.g., PII detected)
    """
    if not query or not query.strip():
        return True, None, []
    
    warnings = []
    query_lower = query.lower()
    
    # Check query length
    if len(query) > 5000:
        return False, "Query exceeds maximum length of 5000 characters", []
    
    # Check for toxicity (BLOCK)
    for pattern in TOXICITY_COMPILED:
        if pattern.search(query_lower):
            logger.warning(f"BLOCKED QUERY (toxicity): {query[:100]}...")
            return False, "Query contains potentially harmful content", []
    
    # Check for prompt injection (BLOCK)
    for pattern in INJECTION_COMPILED:
        if pattern.search(query_lower):
            logger.warning(f"BLOCKED QUERY (injection): {query[:100]}...")
            return False, "Query contains potential prompt injection", []
    
    # Check for PII (WARN but allow)
    for pii_type, pattern in PII_COMPILED.items():
        if pattern.search(query):
            warnings.append(f"Query may contain {pii_type}")
            logger.info(f"PII detected in query ({pii_type}): {query[:50]}...")
    
    return True, None, warnings


def sanitize_query(query: str) -> str:
    """
    Sanitize a query by removing potentially harmful patterns.
    
    Note: This is a secondary defense - validation should happen first.
    """
    if not query:
        return query
    
    # Remove common injection prefixes
    sanitized = query
    
    # Remove system-like prefixes
    sanitized = re.sub(r"^\s*(?:system|user|assistant)\s*:\s*", "", sanitized, flags=re.IGNORECASE)
    
    # Remove special tokens
    sanitized = re.sub(r"<\|[^>]+\|>", "", sanitized)
    sanitized = re.sub(r"\[INST\]|\[/INST\]", "", sanitized)
    
    return sanitized.strip()


# =============================================================================
# Response Validation
# =============================================================================

# Harmful response patterns
HARMFUL_RESPONSE_PATTERNS = [
    r"here(?:'s|\s+is)\s+how\s+to\s+(?:make|build)\s+(?:a\s+)?(?:bomb|weapon)",
    r"step\s*(?:1|one)\s*:\s*(?:obtain|get|find)\s+(?:ingredients|materials)",
]

HARMFUL_RESPONSE_COMPILED = [re.compile(p, re.IGNORECASE) for p in HARMFUL_RESPONSE_PATTERNS]


def validate_response(
    response: str,
    query: str,
    sources: List[dict],
    require_citation: bool = False
) -> Tuple[bool, Optional[str], List[str]]:
    """
    Validate a RAG-generated response.
    
    Args:
        response: The generated response text
        query: Original query
        sources: Retrieved source chunks
        require_citation: Whether citations are required
        
    Returns:
        (is_valid, block_reason, warnings)
    """
    if not response:
        return True, None, []
    
    warnings = []
    
    # Check for harmful content (BLOCK)
    for pattern in HARMFUL_RESPONSE_COMPILED:
        if pattern.search(response):
            logger.warning(f"BLOCKED RESPONSE (harmful): {response[:100]}...")
            return False, "Response contains potentially harmful content", []
    
    # Check for citation presence (WARN if missing)
    if require_citation:
        # Look for citation patterns like [1], [Source 1], etc.
        citation_pattern = r"\[\d+\]|\[Source\s*\d+\]|\[Ref\s*\d+\]"
        if not re.search(citation_pattern, response):
            warnings.append("Response does not contain citations")
    
    # Basic hallucination check (very simplified)
    # In production, use NLI models for this
    if sources:
        # Check if response makes specific claims not in sources
        source_text = " ".join([s.get("content", "") for s in sources]).lower()
        
        # Look for specific numerical claims
        numbers_in_response = set(re.findall(r"\b\d{4,}\b", response))  # 4+ digit numbers
        numbers_in_sources = set(re.findall(r"\b\d{4,}\b", source_text))
        
        unsupported_numbers = numbers_in_response - numbers_in_sources
        if unsupported_numbers:
            warnings.append(f"Response contains numbers not found in sources: {unsupported_numbers}")
    
    return True, None, warnings


# =============================================================================
# Grounding Score
# =============================================================================

def calculate_grounding_score(
    response: str,
    sources: List[dict]
) -> float:
    """
    Calculate a simple grounding score (0-1) for how well the response
    is supported by the sources.
    
    This is a simplified version - production should use NLI models.
    """
    if not response or not sources:
        return 0.0
    
    source_text = " ".join([s.get("content", "") for s in sources]).lower()
    source_words = set(source_text.split())
    
    response_words = set(response.lower().split())
    
    # Calculate overlap
    overlap = response_words & source_words
    
    # Remove common stop words from consideration
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "must", "shall",
                  "can", "need", "to", "of", "in", "for", "on", "with", "at",
                  "by", "from", "as", "into", "through", "during", "before",
                  "after", "above", "below", "between", "under", "again",
                  "further", "then", "once", "here", "there", "when", "where",
                  "why", "how", "all", "each", "few", "more", "most", "other",
                  "some", "such", "no", "nor", "not", "only", "own", "same",
                  "so", "than", "too", "very", "just", "and", "but", "if",
                  "or", "because", "until", "while", "this", "that", "these",
                  "those", "it", "its", "i", "you", "he", "she", "they", "we"}
    
    overlap = overlap - stop_words
    response_content = response_words - stop_words
    
    if not response_content:
        return 1.0  # No content words to check
    
    score = len(overlap) / len(response_content)
    return min(1.0, score)  # Cap at 1.0
