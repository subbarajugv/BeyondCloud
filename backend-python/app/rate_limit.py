"""
Rate Limiting Configuration - Prevent API abuse

Uses slowapi (based on flask-limiter) for rate limiting.

Limits:
- 100 req/min general
- 50 req/min RAG endpoints
- 30 req/min Agent endpoints
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request


def get_user_or_ip(request: Request) -> str:
    """
    Get rate limit key - user ID if authenticated, else IP address.
    This allows per-user rate limiting for authenticated users.
    """
    # Try to get user from auth context
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Extract user_id from token (lightweight, no DB lookup)
        try:
            import jwt
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}  # Just extract claim
            )
            user_id = payload.get("userId")
            if user_id:
                return f"user:{user_id}"
        except:
            pass
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter with user-aware key function
limiter = Limiter(key_func=get_user_or_ip)

# Rate limit decorators for different endpoint types
GENERAL_LIMIT = "100/minute"
RAG_LIMIT = "50/minute"
AGENT_LIMIT = "30/minute"
AUTH_LIMIT = "10/minute"
