"""
LLM-as-a-Judge - Use any configured LLM provider for evaluation

Supports all providers from /api/models:
- llama.cpp (local)
- ollama (local)
- openai (cloud)
- gemini (cloud)
- groq (cloud)

Usage:
    from evaluation.llm_judge import LLMJudge
    
    # Use default provider from config
    judge = LLMJudge()
    
    # Or specify provider/model
    judge = LLMJudge(provider="ollama", model="llama3.2:latest")
    
    # Evaluate
    result = await judge.evaluate_faithfulness(
        output="Paris is the capital of France.",
        context=["Paris is the capital and largest city of France."]
    )
"""
import json
import logging
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.services.provider_service import provider_service

logger = logging.getLogger(__name__)
settings = get_settings()


# Evaluation prompt templates
FAITHFULNESS_PROMPT = """You are an impartial judge evaluating whether an AI assistant's response is faithful to the provided context.

CONTEXT:
{context}

RESPONSE TO EVALUATE:
{output}

TASK: Determine if the response is faithful to the context. A faithful response:
1. Only makes claims that are supported by the context
2. Does not contradict the context
3. Does not hallucinate information not present in the context

Respond in JSON format:
{{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<brief explanation of your score>",
    "unsupported_claims": ["<list any claims not supported by context>"]
}}

JSON Response:"""

RELEVANCE_PROMPT = """You are an impartial judge evaluating whether an AI assistant's response is relevant to the user's question.

USER QUESTION:
{input}

RESPONSE TO EVALUATE:
{output}

TASK: Determine if the response is relevant. A relevant response:
1. Directly addresses the user's question
2. Provides useful information related to the query
3. Does not go off-topic

Respond in JSON format:
{{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<brief explanation of your score>"
}}

JSON Response:"""

COHERENCE_PROMPT = """You are an impartial judge evaluating the coherence and readability of text.

TEXT TO EVALUATE:
{output}

TASK: Evaluate the coherence. A coherent response:
1. Is well-structured and logical
2. Uses clear language
3. Has proper flow between ideas
4. Is easy to understand

Respond in JSON format:
{{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<brief explanation of your score>"
}}

JSON Response:"""

CUSTOM_PROMPT = """You are an impartial judge evaluating text based on specific criteria.

{custom_criteria}

TEXT TO EVALUATE:
{output}

ADDITIONAL CONTEXT:
{context}

Respond in JSON format:
{{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<brief explanation of your score>"
}}

JSON Response:"""


class LLMJudge:
    """
    LLM-as-a-Judge for evaluation using any configured provider.
    
    Automatically uses the provider service to call the appropriate API.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,  # Low temp for consistent judgments
    ):
        """
        Initialize the LLM Judge.
        
        Args:
            provider: LLM provider (llama.cpp, ollama, openai, gemini, groq)
                     Defaults to DEFAULT_LLM_PROVIDER from settings
            model: Model name. If not specified, uses first available model.
            temperature: Sampling temperature (0.0 for deterministic)
        """
        self.provider = provider or settings.default_llm_provider
        self.model = model
        self.temperature = temperature
        
        logger.info(f"LLMJudge initialized with provider={self.provider}")
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return the response text"""
        # Get model if not specified
        model = self.model
        if not model:
            models = await provider_service.get_models(self.provider)
            if models:
                model = models[0].get("id", models[0].get("name", "default"))
            else:
                model = "default"
        
        # Call the provider
        response = await provider_service.chat_completion(
            provider=self.provider,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=500,
        )
        
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling common issues"""
        # Try to extract JSON from response
        response = response.strip()
        
        # Sometimes LLMs wrap in markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Return a default with score 0.5 to indicate uncertainty
            return {
                "score": 0.5,
                "reasoning": f"Failed to parse response: {response[:100]}...",
                "parse_error": str(e),
            }
    
    async def evaluate_faithfulness(
        self,
        output: str,
        context: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluate if output is faithful to context.
        
        Returns:
            Dict with score (0-1), reasoning, and unsupported_claims
        """
        context_str = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(context))
        prompt = FAITHFULNESS_PROMPT.format(context=context_str, output=output)
        
        response = await self._call_llm(prompt)
        return self._parse_json_response(response)
    
    async def evaluate_relevance(
        self,
        input: str,
        output: str,
    ) -> Dict[str, Any]:
        """
        Evaluate if output is relevant to input.
        
        Returns:
            Dict with score (0-1) and reasoning
        """
        prompt = RELEVANCE_PROMPT.format(input=input, output=output)
        
        response = await self._call_llm(prompt)
        return self._parse_json_response(response)
    
    async def evaluate_coherence(
        self,
        output: str,
    ) -> Dict[str, Any]:
        """
        Evaluate the coherence of output text.
        
        Returns:
            Dict with score (0-1) and reasoning
        """
        prompt = COHERENCE_PROMPT.format(output=output)
        
        response = await self._call_llm(prompt)
        return self._parse_json_response(response)
    
    async def evaluate_custom(
        self,
        output: str,
        criteria: str,
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate using custom criteria.
        
        Args:
            output: Text to evaluate
            criteria: Custom evaluation criteria/rubric
            context: Additional context for evaluation
        
        Returns:
            Dict with score (0-1) and reasoning
        """
        prompt = CUSTOM_PROMPT.format(
            custom_criteria=criteria,
            output=output,
            context=context or "None provided",
        )
        
        response = await self._call_llm(prompt)
        return self._parse_json_response(response)
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        context: Optional[List[str]] = None,
        metrics: List[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run multiple evaluations on a Q&A pair.
        
        Args:
            question: The input question
            answer: The generated answer
            context: Retrieved context (for faithfulness)
            metrics: List of metrics to run (default: all)
        
        Returns:
            Dict of metric_name -> result
        """
        metrics = metrics or ["faithfulness", "relevance", "coherence"]
        results = {}
        
        for metric in metrics:
            if metric == "faithfulness" and context:
                results[metric] = await self.evaluate_faithfulness(answer, context)
            elif metric == "relevance":
                results[metric] = await self.evaluate_relevance(question, answer)
            elif metric == "coherence":
                results[metric] = await self.evaluate_coherence(answer)
        
        return results
