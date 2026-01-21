"""
Example Evaluation Tests - Use as template for CI/CD

Run with:
    cd backend-python
    PYTHONPATH=. pytest tests/test_evaluation.py -v

Note: Requires a running LLM provider (ollama, llama.cpp, etc.)
"""
import pytest
import asyncio

# Skip all tests if no LLM provider is available
pytestmark = pytest.mark.skipif(
    True,  # Change to False when LLM is available
    reason="LLM provider not configured for testing"
)


class TestFaithfulness:
    """Test faithfulness evaluation"""
    
    @pytest.mark.asyncio
    async def test_faithful_response(self):
        """Response based on context should be faithful"""
        from evaluation.deepeval_runner import assert_faithfulness
        
        context = [
            "BeyondCloud is an enterprise AI platform.",
            "It supports RAG, Agents, and multiple LLM providers.",
        ]
        answer = "BeyondCloud is an enterprise AI platform that supports RAG and Agents."
        
        result = await assert_faithfulness(
            answer=answer,
            context=context,
            threshold=0.7,
            provider="ollama",  # Configure your provider
        )
        
        assert result.passed
    
    @pytest.mark.asyncio
    async def test_unfaithful_response_fails(self):
        """Response with hallucination should fail"""
        from evaluation.deepeval_runner import assert_faithfulness
        
        context = ["The sky is blue."]
        answer = "The sky is green and has purple polka dots."
        
        with pytest.raises(AssertionError):
            await assert_faithfulness(
                answer=answer,
                context=context,
                threshold=0.7,
                provider="ollama",
            )


class TestRelevance:
    """Test relevance evaluation"""
    
    @pytest.mark.asyncio
    async def test_relevant_response(self):
        """On-topic response should be relevant"""
        from evaluation.deepeval_runner import assert_relevance
        
        question = "What is RAG?"
        answer = "RAG (Retrieval Augmented Generation) combines document retrieval with LLM generation."
        
        result = await assert_relevance(
            question=question,
            answer=answer,
            threshold=0.7,
            provider="ollama",
        )
        
        assert result.passed


class TestFullEvaluation:
    """Test complete evaluation pipeline"""
    
    @pytest.mark.asyncio
    async def test_rag_response_evaluation(self):
        """Full RAG response evaluation"""
        from evaluation.deepeval_runner import evaluate_rag_response
        
        result = await evaluate_rag_response(
            question="What features does BeyondCloud offer?",
            answer="BeyondCloud offers RAG, Agent workflows, and multi-provider LLM support.",
            context=[
                "BeyondCloud provides Retrieval Augmented Generation (RAG).",
                "BeyondCloud supports Agent workflows with tool calling.",
                "BeyondCloud can use multiple LLM providers including Ollama and OpenAI.",
            ],
            provider="ollama",
            threshold=0.7,
        )
        
        print(result.summary)
        assert result.passed, f"Evaluation failed: {result.summary}"


class TestCustomMetrics:
    """Test custom metric evaluation"""
    
    @pytest.mark.asyncio
    async def test_custom_criteria(self):
        """Evaluate with custom criteria"""
        from evaluation.llm_judge import LLMJudge
        
        judge = LLMJudge(provider="ollama")
        
        result = await judge.evaluate_custom(
            output="Thank you for contacting BeyondCloud support! We're happy to help.",
            criteria="""
            Evaluate if the response follows professional customer service guidelines:
            1. Is polite and professional
            2. Uses positive language
            3. Shows willingness to help
            """,
        )
        
        assert result["score"] >= 0.7, f"Custom evaluation failed: {result}"
