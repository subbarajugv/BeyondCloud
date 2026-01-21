"""
Arize Phoenix Integration - Tracing and observability for LLM applications

Provides:
- Phoenix span tracing for RAG and Agents
- Export traces to Phoenix UI
- Evaluation result correlation

Usage:
    from evaluation.phoenix_integration import (
        PhoenixTracer,
        trace_rag_call,
        trace_agent_step,
    )
    
    # Initialize tracer
    tracer = PhoenixTracer()
    await tracer.start()
    
    # Trace RAG calls
    with trace_rag_call(tracer, query="What is RAG?"):
        # ... your RAG logic
        pass
    
    # View in Phoenix UI (default: http://localhost:6006)

Requires: pip install arize-phoenix
"""
import logging
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class PhoenixTracer:
    """
    Arize Phoenix tracer for LLM observability.
    
    Traces:
    - LLM calls with prompts/completions
    - Embedding operations
    - Retrieval operations
    - Agent tool calls
    """
    
    def __init__(
        self,
        project_name: str = "beyondcloud",
        phoenix_url: str = None,
    ):
        self.project_name = project_name
        self.phoenix_url = phoenix_url or os.getenv("PHOENIX_URL", "http://localhost:6006")
        self._session = None
        self._tracer = None
    
    async def start(self):
        """Start Phoenix tracing session"""
        try:
            import phoenix as px
            
            # Launch Phoenix if running locally
            self._session = px.launch_app()
            logger.info(f"Phoenix UI available at: {self._session.url}")
            
            # Get tracer
            from phoenix.trace import tracer
            self._tracer = tracer
            
            return self._session.url
        except ImportError:
            logger.warning(
                "arize-phoenix not installed. "
                "Install with: pip install arize-phoenix"
            )
            return None
    
    def get_tracer(self):
        """Get the Phoenix tracer context"""
        return self._tracer
    
    @contextmanager
    def trace_llm(
        self,
        model: str,
        prompt: str,
        provider: str = "unknown",
    ):
        """Trace an LLM call"""
        if not self._tracer:
            yield
            return
        
        from phoenix.trace import SpanKind
        
        with self._tracer.span(
            name=f"llm:{model}",
            span_kind=SpanKind.LLM,
            attributes={
                "llm.model": model,
                "llm.provider": provider,
                "input.value": prompt,
            }
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status("ERROR", str(e))
                raise
    
    @contextmanager
    def trace_retrieval(
        self,
        query: str,
        top_k: int = 5,
    ):
        """Trace a retrieval operation"""
        if not self._tracer:
            yield
            return
        
        from phoenix.trace import SpanKind
        
        with self._tracer.span(
            name="retrieval",
            span_kind=SpanKind.RETRIEVER,
            attributes={
                "input.value": query,
                "retrieval.top_k": top_k,
            }
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status("ERROR", str(e))
                raise
    
    @contextmanager
    def trace_embedding(
        self,
        model: str = "unknown",
        text_count: int = 1,
    ):
        """Trace an embedding operation"""
        if not self._tracer:
            yield
            return
        
        from phoenix.trace import SpanKind
        
        with self._tracer.span(
            name=f"embedding:{model}",
            span_kind=SpanKind.EMBEDDING,
            attributes={
                "embedding.model": model,
                "embedding.text_count": text_count,
            }
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status("ERROR", str(e))
                raise
    
    @contextmanager
    def trace_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any] = None,
    ):
        """Trace a tool call"""
        if not self._tracer:
            yield
            return
        
        from phoenix.trace import SpanKind
        
        with self._tracer.span(
            name=f"tool:{tool_name}",
            span_kind=SpanKind.TOOL,
            attributes={
                "tool.name": tool_name,
                "tool.arguments": str(arguments or {}),
            }
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status("ERROR", str(e))
                raise
    
    def log_evaluation(
        self,
        span,
        metric_name: str,
        score: float,
        reasoning: str = None,
    ):
        """Log evaluation result to span"""
        if span:
            span.set_attribute(f"eval.{metric_name}.score", score)
            if reasoning:
                span.set_attribute(f"eval.{metric_name}.reasoning", reasoning)


# =============================================================================
# Convenience functions
# =============================================================================

_default_tracer: Optional[PhoenixTracer] = None


def get_phoenix_tracer() -> Optional[PhoenixTracer]:
    """Get the default Phoenix tracer"""
    global _default_tracer
    return _default_tracer


async def init_phoenix(project_name: str = "beyondcloud") -> Optional[str]:
    """Initialize Phoenix tracing"""
    global _default_tracer
    _default_tracer = PhoenixTracer(project_name=project_name)
    return await _default_tracer.start()


@contextmanager
def trace_rag_call(query: str, tracer: PhoenixTracer = None):
    """
    Convenience context manager for tracing RAG calls.
    
    Usage:
        with trace_rag_call("What is RAG?") as span:
            # Retrieval
            docs = retrieve(query)
            span.set_attribute("retrieval.doc_count", len(docs))
            
            # Generation
            answer = generate(query, docs)
            span.set_attribute("output.value", answer)
    """
    tracer = tracer or get_phoenix_tracer()
    if not tracer:
        yield None
        return
    
    with tracer.trace_retrieval(query) as span:
        yield span


@contextmanager
def trace_agent_step(
    step_name: str,
    tracer: PhoenixTracer = None,
):
    """
    Convenience context manager for tracing agent steps.
    
    Usage:
        with trace_agent_step("plan") as span:
            plan = agent.plan(task)
            span.set_attribute("plan", str(plan))
    """
    tracer = tracer or get_phoenix_tracer()
    if not tracer or not tracer._tracer:
        yield None
        return
    
    from phoenix.trace import SpanKind
    
    with tracer._tracer.span(
        name=f"agent:{step_name}",
        span_kind=SpanKind.AGENT,
    ) as span:
        yield span
