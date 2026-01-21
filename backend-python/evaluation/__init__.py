"""
Evaluation Framework - DeepEval + LLM-as-a-Judge

Provides:
- Metric interface for custom scoring
- LLM-as-a-Judge using any configured provider
- DeepEval integration for CI/CD assertions
- Built-in metrics (faithfulness, relevance, etc.)

Usage:
    from evaluation import LLMJudge, FaithfulnessMetric, run_evaluation
    
    # Using LLM-as-a-Judge with any provider
    judge = LLMJudge(provider="ollama", model="llama3.2")
    score = await judge.evaluate(
        question="What is RAG?",
        answer="RAG is Retrieval Augmented Generation...",
        context=["RAG combines retrieval with generation..."]
    )
    
    # Using custom metrics
    metric = FaithfulnessMetric(judge=judge)
    result = await metric.score(output, context)
"""
