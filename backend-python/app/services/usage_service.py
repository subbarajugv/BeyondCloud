"""
Usage Service - Track and aggregate user activity

Provides:
- Increment counters for RAG, Agent, LLM, MCP usage
- Get daily/weekly/monthly stats
- Auto-creates periods as needed
"""
from typing import Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class UsageService:
    """Track user activity for analytics"""
    
    async def increment(
        self,
        db: AsyncSession,
        user_id: str,
        metric: str,
        amount: int = 1,
        period_date: Optional[date] = None,
    ):
        """
        Increment a usage metric
        
        Args:
            db: Database session
            user_id: User ID
            metric: One of: rag_queries, rag_ingestions, rag_chunks_retrieved,
                    agent_tool_calls, agent_approvals, agent_rejections,
                    llm_requests, llm_tokens_input, llm_tokens_output, mcp_tool_calls
            amount: Amount to increment (default 1)
            period_date: Date for the period (default: today)
        """
        if period_date is None:
            period_date = date.today()
        
        # Get period start/end (daily granularity)
        period_start = period_date
        period_end = period_date
        
        # Upsert the metric
        await db.execute(
            text(f"""
                INSERT INTO usage_stats (user_id, period_start, period_end, {metric})
                VALUES (:user_id, :period_start, :period_end, :amount)
                ON CONFLICT (user_id, period_start, period_end)
                DO UPDATE SET {metric} = usage_stats.{metric} + :amount,
                              updated_at = NOW()
            """),
            {
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end,
                "amount": amount,
            }
        )
        await db.commit()
    
    async def get_stats(
        self,
        db: AsyncSession,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get aggregated stats for the last N days"""
        start_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            text("""
                SELECT 
                    COALESCE(SUM(rag_queries), 0) as rag_queries,
                    COALESCE(SUM(rag_ingestions), 0) as rag_ingestions,
                    COALESCE(SUM(rag_chunks_retrieved), 0) as rag_chunks_retrieved,
                    COALESCE(SUM(agent_tool_calls), 0) as agent_tool_calls,
                    COALESCE(SUM(agent_approvals), 0) as agent_approvals,
                    COALESCE(SUM(agent_rejections), 0) as agent_rejections,
                    COALESCE(SUM(llm_requests), 0) as llm_requests,
                    COALESCE(SUM(llm_tokens_input), 0) as llm_tokens_input,
                    COALESCE(SUM(llm_tokens_output), 0) as llm_tokens_output,
                    COALESCE(SUM(mcp_tool_calls), 0) as mcp_tool_calls
                FROM usage_stats
                WHERE user_id = :user_id AND period_start >= :start_date
            """),
            {"user_id": user_id, "start_date": start_date}
        )
        row = result.fetchone()
        
        if row:
            return dict(row._mapping)
        
        return {
            "rag_queries": 0,
            "rag_ingestions": 0,
            "rag_chunks_retrieved": 0,
            "agent_tool_calls": 0,
            "agent_approvals": 0,
            "agent_rejections": 0,
            "llm_requests": 0,
            "llm_tokens_input": 0,
            "llm_tokens_output": 0,
            "mcp_tool_calls": 0,
        }
    
    async def get_daily_breakdown(
        self,
        db: AsyncSession,
        user_id: str,
        days: int = 7,
    ) -> list:
        """Get daily breakdown for the last N days"""
        start_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            text("""
                SELECT period_start as date,
                       rag_queries, agent_tool_calls, llm_requests
                FROM usage_stats
                WHERE user_id = :user_id AND period_start >= :start_date
                ORDER BY period_start DESC
            """),
            {"user_id": user_id, "start_date": start_date}
        )
        
        return [dict(row._mapping) for row in result.fetchall()]


# Singleton instance
usage_service = UsageService()
