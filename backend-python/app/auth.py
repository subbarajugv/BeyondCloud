"""
Authentication Module - JWT validation for Python backend

Validates JWTs issued by the Node.js backend using the same secret.
This allows the Python backend to authenticate requests forwarded from Node.js.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from functools import wraps

import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.logging_config import get_logger

logger = get_logger(__name__)

# JWT Configuration - must match Node.js backend
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"


@dataclass
class User:
    """Authenticated user from JWT"""
    id: str
    email: str


# Security scheme for OpenAPI docs
security = HTTPBearer(auto_error=False)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Returns the payload if valid, None if invalid.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_user_from_token(token: str) -> Optional[User]:
    """
    Extract user information from a JWT token.
    
    Returns User object if valid, None if invalid.
    """
    payload = decode_token(token)
    if not payload:
        return None
    
    user_id = payload.get("userId")
    email = payload.get("email")
    
    if not user_id:
        return None
    
    return User(id=user_id, email=email or "")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    # Try to get token from Authorization header
    token = None
    
    if credentials:
        token = credentials.credentials
    else:
        # Try to get from X-User-Token header (for internal service calls)
        token = request.headers.get("X-User-Token")
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required"}
        )
    
    user = get_user_from_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"}
        )
    
    return user


async def get_current_user_id(
    user: User = Depends(get_current_user),
) -> str:
    """
    FastAPI dependency to get just the user ID.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user_id: str = Depends(get_current_user_id)):
            ...
    """
    return user.id


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    FastAPI dependency for optional authentication.
    Returns None if not authenticated instead of raising an error.
    """
    token = None
    
    if credentials:
        token = credentials.credentials
    else:
        token = request.headers.get("X-User-Token")
    
    if not token:
        return None
    
    return get_user_from_token(token)


async def get_optional_user_id(
    user: Optional[User] = Depends(get_optional_user),
) -> Optional[str]:
    """
    FastAPI dependency to get optional user ID.
    Returns None if not authenticated.
    """
    return user.id if user else None
