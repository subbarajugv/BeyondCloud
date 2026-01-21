"""
Metric Interface - Extensible scoring system

Provides:
- Abstract Metric base class
- Built-in metrics (Faithfulness, Relevance, Coherence)
- Custom metric creation support

Usage:
    from evaluation.metrics import FaithfulnessMetric, RelevanceMetric
    
    metric = FaithfulnessMetric()
    result = await metric.score(
        output="The capital of France is Paris.",
        context=["Paris is the capital and largest city of France."]
    )
    print(result.score, result.reasoning)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class MetricType(str, Enum):
    """Types of evaluation metrics"""
    FAITHFULNESS = "faithfulness"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    HARMFULNESS = "harmfulness"
    CUSTOM = "custom"


@dataclass
class MetricResult:
    """Result from a metric evaluation"""
    score: float  # 0.0 to 1.0
    passed: bool  # True if score >= threshold
    metric_name: str
    reasoning: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_score(cls, score: float, metric_name: str, threshold: float = 0.7, reasoning: str = None):
        return cls(
            score=score,
            passed=score >= threshold,
            metric_name=metric_name,
            reasoning=reasoning,
        )


class Metric(ABC):
    """
    Abstract base class for evaluation metrics.
    
    Extend this to create custom domain-specific metrics.
    
    Example:
        class BrandVoiceMetric(Metric):
            name = "brand_voice"
            
            async def score(self, output: str, context: dict) -> MetricResult:
                # Custom scoring logic
                score = await self._check_brand_alignment(output)
                return MetricResult.from_score(score, self.name)
    """
    
    name: str = "base_metric"
    description: str = "Base metric"
    threshold: float = 0.7
    
    @abstractmethod
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        """
        Score the output.
        
        Args:
            output: The generated text to evaluate
            context: Optional context dict with keys like:
                     - input: Original input/question
                     - retrieved_context: RAG retrieved chunks
                     - expected_output: Ground truth (if available)
        
        Returns:
            MetricResult with score and reasoning
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(threshold={self.threshold})"


class FaithfulnessMetric(Metric):
    """
    Measures if the output is faithful to the provided context.
    Uses LLM-as-a-Judge for evaluation.
    
    Score interpretation:
        1.0: Fully faithful, all claims supported by context
        0.5: Partially faithful, some claims unsupported
        0.0: Not faithful, contradicts or fabricates information
    """
    
    name = "faithfulness"
    description = "Measures if output is faithful to context"
    
    def __init__(self, judge=None, threshold: float = 0.7):
        self.judge = judge
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        if not self.judge:
            raise ValueError("FaithfulnessMetric requires an LLM judge")
        
        retrieved_context = context.get("retrieved_context", []) if context else []
        
        result = await self.judge.evaluate_faithfulness(
            output=output,
            context=retrieved_context,
        )
        
        return MetricResult.from_score(
            score=result["score"],
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=result.get("reasoning"),
        )


class RelevanceMetric(Metric):
    """
    Measures if the output is relevant to the input question.
    
    Score interpretation:
        1.0: Highly relevant, directly answers the question
        0.5: Partially relevant, tangentially related
        0.0: Not relevant, off-topic
    """
    
    name = "relevance"
    description = "Measures if output is relevant to input"
    
    def __init__(self, judge=None, threshold: float = 0.7):
        self.judge = judge
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        if not self.judge:
            raise ValueError("RelevanceMetric requires an LLM judge")
        
        input_text = context.get("input", "") if context else ""
        
        result = await self.judge.evaluate_relevance(
            input=input_text,
            output=output,
        )
        
        return MetricResult.from_score(
            score=result["score"],
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=result.get("reasoning"),
        )


class CoherenceMetric(Metric):
    """
    Measures the coherence and readability of the output.
    
    Score interpretation:
        1.0: Highly coherent, well-structured, easy to understand
        0.5: Somewhat coherent, minor issues
        0.0: Incoherent, difficult to understand
    """
    
    name = "coherence"
    description = "Measures output coherence and readability"
    
    def __init__(self, judge=None, threshold: float = 0.7):
        self.judge = judge
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        if not self.judge:
            raise ValueError("CoherenceMetric requires an LLM judge")
        
        result = await self.judge.evaluate_coherence(output=output)
        
        return MetricResult.from_score(
            score=result["score"],
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=result.get("reasoning"),
        )


# Registry of built-in metrics
BUILTIN_METRICS = {
    "faithfulness": FaithfulnessMetric,
    "relevance": RelevanceMetric,
    "coherence": CoherenceMetric,
}


def get_metric(name: str, **kwargs) -> Metric:
    """Get a metric by name"""
    if name not in BUILTIN_METRICS:
        raise ValueError(f"Unknown metric: {name}. Available: {list(BUILTIN_METRICS.keys())}")
    return BUILTIN_METRICS[name](**kwargs)
