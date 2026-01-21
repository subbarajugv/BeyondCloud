"""
DeepEval Runner - CI/CD integration for automated evaluation

Provides:
- DeepEval test assertions
- Integration with pytest
- Batch evaluation runner

Usage in pytest:
    from evaluation.deepeval_runner import assert_faithfulness, evaluate_rag_response
    
    def test_rag_faithfulness():
        result = await evaluate_rag_response(
            question="What is BeyondCloud?",
            answer="BeyondCloud is an AI platform...",
            context=["BeyondCloud is an enterprise AI platform..."]
        )
        assert result.passed, f"Faithfulness failed: {result.reasoning}"

CI/CD Usage:
    pytest tests/test_evaluation.py -v --tb=short
    # Fails if any evaluation score < threshold
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .metrics import Metric, MetricResult, FaithfulnessMetric, RelevanceMetric, CoherenceMetric
from .llm_judge import LLMJudge

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Combined result from multiple metrics"""
    question: str
    answer: str
    metrics: Dict[str, MetricResult]
    passed: bool  # True if all metrics passed
    
    @property
    def summary(self) -> str:
        lines = [f"Q: {self.question[:50]}..."]
        for name, result in self.metrics.items():
            status = "✓" if result.passed else "✗"
            lines.append(f"  {status} {name}: {result.score:.2f}")
        return "\n".join(lines)


class EvaluationRunner:
    """
    Runs batch evaluations with configurable metrics.
    
    Example:
        runner = EvaluationRunner(provider="ollama", model="llama3.2")
        results = await runner.evaluate_batch(test_cases)
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metrics: List[str] = None,
        thresholds: Dict[str, float] = None,
    ):
        """
        Initialize the runner.
        
        Args:
            provider: LLM provider for judge
            model: Model name for judge
            metrics: List of metrics to run (default: all)
            thresholds: Custom thresholds per metric
        """
        self.judge = LLMJudge(provider=provider, model=model)
        self.metrics = metrics or ["faithfulness", "relevance", "coherence"]
        self.thresholds = thresholds or {}
        
        # Initialize metric instances
        self._metric_instances: Dict[str, Metric] = {}
        for name in self.metrics:
            threshold = self.thresholds.get(name, 0.7)
            if name == "faithfulness":
                self._metric_instances[name] = FaithfulnessMetric(judge=self.judge, threshold=threshold)
            elif name == "relevance":
                self._metric_instances[name] = RelevanceMetric(judge=self.judge, threshold=threshold)
            elif name == "coherence":
                self._metric_instances[name] = CoherenceMetric(judge=self.judge, threshold=threshold)
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        context: List[str] = None,
    ) -> EvaluationResult:
        """Evaluate a single Q&A pair"""
        results = {}
        
        for name, metric in self._metric_instances.items():
            ctx = {
                "input": question,
                "retrieved_context": context or [],
            }
            result = await metric.score(output=answer, context=ctx)
            results[name] = result
        
        all_passed = all(r.passed for r in results.values())
        
        return EvaluationResult(
            question=question,
            answer=answer,
            metrics=results,
            passed=all_passed,
        )
    
    async def evaluate_batch(
        self,
        test_cases: List[Dict[str, Any]],
    ) -> List[EvaluationResult]:
        """
        Evaluate multiple test cases.
        
        Args:
            test_cases: List of dicts with keys: question, answer, context (optional)
        
        Returns:
            List of EvaluationResults
        """
        results = []
        for case in test_cases:
            result = await self.evaluate(
                question=case["question"],
                answer=case["answer"],
                context=case.get("context", []),
            )
            results.append(result)
            logger.info(f"Evaluated: {result.summary}")
        
        return results


# =============================================================================
# Pytest-compatible assertions
# =============================================================================

async def evaluate_rag_response(
    question: str,
    answer: str,
    context: List[str] = None,
    provider: str = None,
    model: str = None,
    threshold: float = 0.7,
) -> EvaluationResult:
    """
    Evaluate a RAG response with all metrics.
    
    Use in pytest:
        result = await evaluate_rag_response(...)
        assert result.passed
    """
    runner = EvaluationRunner(
        provider=provider,
        model=model,
        thresholds={
            "faithfulness": threshold,
            "relevance": threshold,
            "coherence": threshold,
        }
    )
    return await runner.evaluate(question, answer, context)


async def assert_faithfulness(
    answer: str,
    context: List[str],
    threshold: float = 0.7,
    provider: str = None,
    model: str = None,
) -> MetricResult:
    """
    Assert that answer is faithful to context.
    
    Raises AssertionError if faithfulness score < threshold.
    """
    judge = LLMJudge(provider=provider, model=model)
    metric = FaithfulnessMetric(judge=judge, threshold=threshold)
    
    result = await metric.score(
        output=answer,
        context={"retrieved_context": context},
    )
    
    if not result.passed:
        raise AssertionError(
            f"Faithfulness assertion failed: score={result.score:.2f} "
            f"(threshold={threshold}). Reasoning: {result.reasoning}"
        )
    
    return result


async def assert_relevance(
    question: str,
    answer: str,
    threshold: float = 0.7,
    provider: str = None,
    model: str = None,
) -> MetricResult:
    """
    Assert that answer is relevant to question.
    
    Raises AssertionError if relevance score < threshold.
    """
    judge = LLMJudge(provider=provider, model=model)
    metric = RelevanceMetric(judge=judge, threshold=threshold)
    
    result = await metric.score(
        output=answer,
        context={"input": question},
    )
    
    if not result.passed:
        raise AssertionError(
            f"Relevance assertion failed: score={result.score:.2f} "
            f"(threshold={threshold}). Reasoning: {result.reasoning}"
        )
    
    return result


# =============================================================================
# DeepEval Integration (when deepeval is installed)
# =============================================================================

def create_deepeval_test(
    question: str,
    answer: str,
    context: List[str] = None,
    expected_output: str = None,
):
    """
    Create a DeepEval test case.
    
    Requires: pip install deepeval
    
    Usage:
        from deepeval import assert_test
        from deepeval.metrics import FaithfulnessMetric
        
        test_case = create_deepeval_test(...)
        assert_test(test_case, [FaithfulnessMetric(threshold=0.7)])
    """
    try:
        from deepeval.test_case import LLMTestCase
        
        return LLMTestCase(
            input=question,
            actual_output=answer,
            retrieval_context=context or [],
            expected_output=expected_output,
        )
    except ImportError:
        raise ImportError(
            "deepeval package required for DeepEval integration. "
            "Install with: pip install deepeval"
        )
