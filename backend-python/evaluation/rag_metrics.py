"""
RAG-Specific Metrics - Context quality and retrieval evaluation

Provides:
- Context Precision: Are retrieved docs relevant?
- Context Recall: Did we retrieve all relevant docs?
- Answer Similarity: Does answer match expected?
- Optional RAGAS integration

Usage:
    from evaluation.rag_metrics import (
        ContextPrecisionMetric,
        ContextRecallMetric,
        AnswerSimilarityMetric,
        RAGASEvaluator,  # Optional RAGAS wrapper
    )
    
    # Using embedding-based similarity
    metric = AnswerSimilarityMetric()
    result = await metric.score(
        output="Paris is the capital of France.",
        context={"expected_output": "The capital of France is Paris."}
    )
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .metrics import Metric, MetricResult

logger = logging.getLogger(__name__)


class ContextPrecisionMetric(Metric):
    """
    Measures precision of retrieved context.
    
    Precision = (relevant retrieved docs) / (total retrieved docs)
    
    Uses embedding similarity to determine relevance.
    """
    
    name = "context_precision"
    description = "Measures if retrieved contexts are relevant to the question"
    
    def __init__(
        self,
        threshold: float = 0.7,
        similarity_threshold: float = 0.5,
        embedder=None,
    ):
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold
        self._embedder = embedder
    
    async def _get_embedder(self):
        """Lazy load embedder"""
        if not self._embedder:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                raise ImportError(
                    "sentence-transformers required for embedding metrics. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedder
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        question = context.get("input", "") if context else ""
        retrieved = context.get("retrieved_context", []) if context else []
        
        if not retrieved:
            return MetricResult.from_score(1.0, self.name, self.threshold, "No context to evaluate")
        
        embedder = await self._get_embedder()
        
        # Embed question and contexts
        q_emb = embedder.encode(question, convert_to_tensor=True)
        ctx_embs = embedder.encode(retrieved, convert_to_tensor=True)
        
        # Calculate similarities
        from torch.nn.functional import cosine_similarity
        similarities = [cosine_similarity(q_emb.unsqueeze(0), c.unsqueeze(0)).item() for c in ctx_embs]
        
        # Count relevant (above threshold)
        relevant_count = sum(1 for s in similarities if s >= self.similarity_threshold)
        precision = relevant_count / len(retrieved)
        
        return MetricResult.from_score(
            score=precision,
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=f"{relevant_count}/{len(retrieved)} contexts relevant",
        )


class ContextRecallMetric(Metric):
    """
    Measures recall of retrieval.
    
    Requires ground truth context to compare against.
    Recall = (relevant retrieved) / (total relevant in corpus)
    """
    
    name = "context_recall"
    description = "Measures if all relevant contexts were retrieved"
    
    def __init__(
        self,
        threshold: float = 0.7,
        similarity_threshold: float = 0.5,
        embedder=None,
    ):
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold
        self._embedder = embedder
    
    async def _get_embedder(self):
        if not self._embedder:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                raise ImportError("sentence-transformers required")
        return self._embedder
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        retrieved = context.get("retrieved_context", []) if context else []
        ground_truth = context.get("ground_truth_context", []) if context else []
        
        if not ground_truth:
            return MetricResult.from_score(
                1.0, self.name, self.threshold,
                "No ground truth context - skipping recall"
            )
        
        embedder = await self._get_embedder()
        
        gt_embs = embedder.encode(ground_truth, convert_to_tensor=True)
        ret_embs = embedder.encode(retrieved, convert_to_tensor=True)
        
        # For each ground truth, check if it was retrieved
        from torch.nn.functional import cosine_similarity
        found_count = 0
        for gt in gt_embs:
            max_sim = max(cosine_similarity(gt.unsqueeze(0), r.unsqueeze(0)).item() for r in ret_embs) if len(ret_embs) > 0 else 0
            if max_sim >= self.similarity_threshold:
                found_count += 1
        
        recall = found_count / len(ground_truth)
        
        return MetricResult.from_score(
            score=recall,
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=f"{found_count}/{len(ground_truth)} ground truth contexts found",
        )


class AnswerSimilarityMetric(Metric):
    """
    Measures semantic similarity between generated and expected answer.
    
    Uses embedding cosine similarity.
    """
    
    name = "answer_similarity"
    description = "Measures semantic similarity to expected answer"
    
    def __init__(self, threshold: float = 0.7, embedder=None):
        self.threshold = threshold
        self._embedder = embedder
    
    async def _get_embedder(self):
        if not self._embedder:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                raise ImportError("sentence-transformers required")
        return self._embedder
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        expected = context.get("expected_output", "") if context else ""
        
        if not expected:
            return MetricResult.from_score(
                1.0, self.name, self.threshold,
                "No expected output - skipping similarity"
            )
        
        embedder = await self._get_embedder()
        from torch.nn.functional import cosine_similarity
        
        out_emb = embedder.encode(output, convert_to_tensor=True)
        exp_emb = embedder.encode(expected, convert_to_tensor=True)
        
        similarity = cosine_similarity(out_emb.unsqueeze(0), exp_emb.unsqueeze(0)).item()
        
        return MetricResult.from_score(
            score=similarity,
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=f"Cosine similarity: {similarity:.3f}",
        )


# =============================================================================
# RAGAS Integration (Optional)
# =============================================================================

class RAGASEvaluator:
    """
    Wrapper for RAGAS evaluation library.
    
    RAGAS provides comprehensive RAG metrics:
    - Faithfulness
    - Answer Relevancy
    - Context Precision
    - Context Recall
    
    Requires: pip install ragas
    
    Usage:
        evaluator = RAGASEvaluator()
        results = await evaluator.evaluate(
            questions=["What is RAG?"],
            answers=["RAG is..."],
            contexts=[["RAG combines..."]],
            ground_truths=["RAG is Retrieval Augmented Generation"]
        )
    """
    
    def __init__(self, llm_model: str = None):
        self.llm_model = llm_model
        self._ragas = None
    
    def _ensure_ragas(self):
        if self._ragas is None:
            try:
                import ragas
                from ragas.metrics import (
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                )
                self._ragas = {
                    "ragas": ragas,
                    "metrics": [faithfulness, answer_relevancy, context_precision, context_recall],
                }
            except ImportError:
                raise ImportError(
                    "RAGAS required for RAG evaluation. "
                    "Install with: pip install ragas"
                )
        return self._ragas
    
    async def evaluate(
        self,
        questions: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: List[str] = None,
    ) -> Dict[str, float]:
        """
        Run RAGAS evaluation.
        
        Returns:
            Dict with metric names and scores
        """
        ragas_lib = self._ensure_ragas()
        from datasets import Dataset
        
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
        }
        if ground_truths:
            data["ground_truth"] = ground_truths
        
        dataset = Dataset.from_dict(data)
        
        from ragas import evaluate
        result = evaluate(dataset, metrics=ragas_lib["metrics"])
        
        return dict(result)
