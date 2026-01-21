"""
Agent-Specific Metrics - Evaluate agentic workflows

Provides:
- Tool Success Rate: Did tools execute successfully?
- Plan Adherence: Did agent follow the plan?
- Task Completion: Was the task completed?
- Step Efficiency: Was the task done efficiently?

Usage:
    from evaluation.agent_metrics import (
        ToolSuccessMetric,
        PlanAdherenceMetric,
        TaskCompletionMetric,
        AgentTraceEvaluator,
    )
    
    # Evaluate from agent trace
    evaluator = AgentTraceEvaluator()
    results = await evaluator.evaluate(trace)
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .metrics import Metric, MetricResult

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call in an agent trace"""
    name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class AgentStep:
    """Represents a step in an agent workflow"""
    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    observation: Optional[str] = None


@dataclass
class AgentTrace:
    """Complete trace of an agent execution"""
    task: str
    steps: List[AgentStep]
    final_answer: Optional[str] = None
    success: bool = True
    total_tokens: int = 0
    total_latency_ms: float = 0


class ToolSuccessMetric(Metric):
    """
    Measures tool execution success rate.
    
    Score = (successful tool calls) / (total tool calls)
    """
    
    name = "tool_success_rate"
    description = "Measures percentage of successful tool executions"
    
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        trace: AgentTrace = context.get("trace") if context else None
        
        if not trace or not trace.steps:
            return MetricResult.from_score(1.0, self.name, self.threshold, "No trace data")
        
        total_calls = 0
        successful_calls = 0
        
        for step in trace.steps:
            for tool_call in step.tool_calls:
                total_calls += 1
                if tool_call.success:
                    successful_calls += 1
        
        if total_calls == 0:
            return MetricResult.from_score(1.0, self.name, self.threshold, "No tool calls")
        
        success_rate = successful_calls / total_calls
        
        return MetricResult.from_score(
            score=success_rate,
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=f"{successful_calls}/{total_calls} tool calls succeeded",
        )


class TaskCompletionMetric(Metric):
    """
    Measures if the agent completed the task.
    
    Uses LLM judge to determine if final answer satisfies task.
    """
    
    name = "task_completion"
    description = "Measures if agent completed the assigned task"
    
    def __init__(self, judge=None, threshold: float = 0.7):
        self.judge = judge
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        trace: AgentTrace = context.get("trace") if context else None
        
        if not trace:
            return MetricResult.from_score(0.5, self.name, self.threshold, "No trace data")
        
        if not self.judge:
            # Fallback: check if trace.success is True
            score = 1.0 if trace.success else 0.0
            return MetricResult.from_score(
                score, self.name, self.threshold,
                f"Task {'completed' if trace.success else 'failed'} (no judge)"
            )
        
        # Use LLM judge
        result = await self.judge.evaluate_custom(
            output=trace.final_answer or "",
            criteria=f"""
            Evaluate if the agent successfully completed the following task:
            TASK: {trace.task}
            
            Consider:
            1. Did the agent produce a relevant answer?
            2. Did the agent use appropriate tools?
            3. Is the final answer correct and complete?
            """,
            context=f"Steps taken: {len(trace.steps)}",
        )
        
        return MetricResult.from_score(
            score=result["score"],
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=result.get("reasoning"),
        )


class StepEfficiencyMetric(Metric):
    """
    Measures step efficiency.
    
    Penalizes excessive steps, retries, and failed tool calls.
    """
    
    name = "step_efficiency"
    description = "Measures if agent completed task efficiently"
    
    def __init__(
        self,
        threshold: float = 0.7,
        max_expected_steps: int = 5,
    ):
        self.threshold = threshold
        self.max_expected_steps = max_expected_steps
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        trace: AgentTrace = context.get("trace") if context else None
        
        if not trace:
            return MetricResult.from_score(0.5, self.name, self.threshold, "No trace data")
        
        actual_steps = len(trace.steps)
        
        # Calculate efficiency score
        if actual_steps <= self.max_expected_steps:
            efficiency = 1.0
        else:
            # Decay score for extra steps
            excess = actual_steps - self.max_expected_steps
            efficiency = max(0.0, 1.0 - (excess * 0.1))
        
        # Penalize failed tool calls
        failed_calls = sum(
            1 for step in trace.steps
            for tc in step.tool_calls
            if not tc.success
        )
        efficiency -= failed_calls * 0.1
        efficiency = max(0.0, efficiency)
        
        return MetricResult.from_score(
            score=efficiency,
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=f"{actual_steps} steps (expected ≤{self.max_expected_steps}), {failed_calls} failed calls",
        )


class PlanAdherenceMetric(Metric):
    """
    Measures if agent adhered to a predefined plan.
    
    Requires expected_plan in context.
    """
    
    name = "plan_adherence"
    description = "Measures if agent followed the expected plan"
    
    def __init__(self, judge=None, threshold: float = 0.7):
        self.judge = judge
        self.threshold = threshold
    
    async def score(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MetricResult:
        trace: AgentTrace = context.get("trace") if context else None
        expected_plan = context.get("expected_plan", []) if context else []
        
        if not expected_plan:
            return MetricResult.from_score(
                1.0, self.name, self.threshold,
                "No expected plan - skipping adherence check"
            )
        
        if not self.judge:
            return MetricResult.from_score(
                0.5, self.name, self.threshold,
                "Plan adherence requires LLM judge"
            )
        
        # Build actual actions from trace
        actual_actions = [
            step.action or f"step_{step.step_number}"
            for step in (trace.steps if trace else [])
        ]
        
        result = await self.judge.evaluate_custom(
            output=str(actual_actions),
            criteria=f"""
            Compare the actual actions taken with the expected plan:
            
            EXPECTED PLAN: {expected_plan}
            ACTUAL ACTIONS: {actual_actions}
            
            Score 1.0 if actions match the plan.
            Score 0.5 if partially matches.
            Score 0.0 if completely different.
            """,
        )
        
        return MetricResult.from_score(
            score=result["score"],
            metric_name=self.name,
            threshold=self.threshold,
            reasoning=result.get("reasoning"),
        )


# =============================================================================
# Agent Trace Evaluator
# =============================================================================

class AgentTraceEvaluator:
    """
    Evaluates complete agent traces.
    
    Usage:
        evaluator = AgentTraceEvaluator(judge=LLMJudge())
        results = await evaluator.evaluate(trace)
    """
    
    def __init__(
        self,
        judge=None,
        metrics: List[str] = None,
    ):
        self.judge = judge
        self.metrics = metrics or [
            "tool_success_rate",
            "task_completion",
            "step_efficiency",
        ]
        
        self._metric_instances: Dict[str, Metric] = {
            "tool_success_rate": ToolSuccessMetric(),
            "task_completion": TaskCompletionMetric(judge=judge),
            "step_efficiency": StepEfficiencyMetric(),
            "plan_adherence": PlanAdherenceMetric(judge=judge),
        }
    
    async def evaluate(
        self,
        trace: AgentTrace,
        expected_plan: List[str] = None,
    ) -> Dict[str, MetricResult]:
        """Evaluate an agent trace"""
        results = {}
        
        ctx = {"trace": trace}
        if expected_plan:
            ctx["expected_plan"] = expected_plan
        
        for name in self.metrics:
            if name not in self._metric_instances:
                continue
            metric = self._metric_instances[name]
            result = await metric.score(output=trace.final_answer or "", context=ctx)
            results[name] = result
        
        return results
