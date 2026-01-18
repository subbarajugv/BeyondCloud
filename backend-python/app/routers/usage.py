"""
Usage Router - API endpoints for usage analytics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.usage_service import usage_service

router = APIRouter(prefix="/usage", tags=["Usage"])


# TODO: Replace with actual auth middleware
async def get_current_user_id() -> str:
    """Temporary: Get user ID from auth (hardcoded for now)"""
    return "00000000-0000-0000-0000-000000000001"


@router.get("/stats")
async def get_usage_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get aggregated usage stats for the current user
    
    Args:
        days: Number of days to aggregate (default: 30)
    """
    stats = await usage_service.get_stats(db, user_id, days)
    return {
        "user_id": user_id,
        "period_days": days,
        "stats": stats,
    }


@router.get("/daily")
async def get_daily_breakdown(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get daily usage breakdown for the current user
    
    Args:
        days: Number of days (default: 7)
    """
    breakdown = await usage_service.get_daily_breakdown(db, user_id, days)
    return {
        "user_id": user_id,
        "period_days": days,
        "daily": breakdown,
    }
