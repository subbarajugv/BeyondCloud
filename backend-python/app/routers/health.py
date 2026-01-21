"""
Deep Health Checks Router - Enterprise-grade health monitoring

Provides:
- /health/live - Kubernetes liveness probe (is the process running?)
- /health/ready - Kubernetes readiness probe (is it ready to serve traffic?)
- /health/deep - Detailed health with all dependencies

Usage in main.py:
    from app.routers.health import router as health_router
    app.include_router(health_router)
"""
from fastapi import APIRouter, Response
from datetime import datetime
import asyncio
import time
import os
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health/live")
async def liveness():
    """
    Kubernetes liveness probe.
    Returns 200 if the process is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """
    Kubernetes readiness probe.
    Returns 200 if ready to serve traffic, 503 otherwise.
    Checks database connectivity only (fast check).
    """
    try:
        db_ok = await check_database(timeout=2.0)
        if db_ok:
            return {"status": "ready"}
        return Response(
            content='{"status": "not_ready", "reason": "database"}',
            status_code=503,
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=f'{{"status": "not_ready", "reason": "{str(e)}"}}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/deep")
async def deep_health():
    """
    Deep health check for monitoring dashboards.
    Checks all dependencies and reports their status.
    
    Returns:
        - status: "healthy" | "degraded" | "unhealthy"
        - checks: Individual check results
        - latency: Response time in ms
    """
    start = time.time()
    
    # Run all checks concurrently
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_llm_provider(),
        return_exceptions=True
    )
    
    checks = {
        "database": _format_result(results[0], "database"),
        "redis": _format_result(results[1], "redis"),
        "llm_provider": _format_result(results[2], "llm_provider"),
    }
    
    # Determine overall status
    statuses = [c["status"] for c in checks.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
        status_code = 200
    elif checks["database"]["status"] == "unhealthy":
        overall = "unhealthy"
        status_code = 503
    else:
        overall = "degraded"
        status_code = 200
    
    latency_ms = round((time.time() - start) * 1000, 2)
    
    return Response(
        content=_json_dumps({
            "status": overall,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "beyondcloud-api",
            "version": "1.0.0",
            "latency_ms": latency_ms,
            "checks": checks,
        }),
        status_code=status_code,
        media_type="application/json"
    )


def _format_result(result, name: str) -> dict:
    """Format a check result, handling exceptions"""
    if isinstance(result, Exception):
        logger.warning(f"Health check '{name}' failed: {result}")
        return {
            "status": "unhealthy",
            "error": str(result),
            "latency_ms": None,
        }
    return result


def _json_dumps(obj) -> str:
    """JSON dumps with datetime handling"""
    import json
    return json.dumps(obj, default=str)


async def check_database(timeout: float = 5.0) -> dict:
    """Check PostgreSQL connectivity and latency"""
    from app.database import async_session
    from sqlalchemy import text
    
    start = time.time()
    try:
        async with async_session() as session:
            # Simple query to check connectivity
            result = await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=timeout
            )
            result.fetchone()
            
            # Check pgvector extension
            ext_result = await asyncio.wait_for(
                session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )),
                timeout=timeout
            )
            pgvector_ok = ext_result.scalar()
        
        latency = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency,
            "pgvector": pgvector_ok,
        }
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "timeout",
            "latency_ms": timeout * 1000,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


async def check_redis(timeout: float = 2.0) -> dict:
    """Check Redis connectivity (optional dependency)"""
    start = time.time()
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return {
            "status": "skipped",
            "reason": "REDIS_URL not configured",
            "latency_ms": None,
        }
    
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(redis_url)
        await asyncio.wait_for(client.ping(), timeout=timeout)
        await client.close()
        
        latency = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency,
        }
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "timeout",
            "latency_ms": timeout * 1000,
        }
    except ImportError:
        return {
            "status": "skipped",
            "reason": "redis package not installed",
            "latency_ms": None,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


async def check_llm_provider(timeout: float = 5.0) -> dict:
    """Check default LLM provider connectivity"""
    start = time.time()
    
    provider = settings.default_llm_provider
    provider_config = settings.get_provider_config().get(provider, {})
    base_url = provider_config.get("base_url", "")
    
    if not base_url:
        return {
            "status": "skipped",
            "reason": f"No URL configured for {provider}",
            "latency_ms": None,
        }
    
    try:
        import httpx
        
        # Try to hit the models endpoint (common for OpenAI-compatible APIs)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/models")
            
            latency = round((time.time() - start) * 1000, 2)
            
            if response.status_code in (200, 401):  # 401 = auth error but reachable
                return {
                    "status": "healthy",
                    "provider": provider,
                    "latency_ms": latency,
                }
            else:
                return {
                    "status": "degraded",
                    "provider": provider,
                    "status_code": response.status_code,
                    "latency_ms": latency,
                }
    except httpx.TimeoutException:
        return {
            "status": "unhealthy",
            "provider": provider,
            "error": "timeout",
            "latency_ms": timeout * 1000,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": provider,
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
