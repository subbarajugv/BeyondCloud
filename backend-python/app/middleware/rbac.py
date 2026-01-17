"""
RBAC Middleware - Role-based access control for Python/FastAPI

Usage:
    @router.get("/admin", dependencies=[require_role("admin", "owner")])
    async def admin_endpoint(): ...
    
    @router.post("/agent", dependencies=[require_min_role("agent_user")])
    async def agent_endpoint(): ...
"""
from typing import List, Optional
from fastapi import HTTPException, Depends, Request
from functools import wraps

# Role hierarchy (higher index = more permissions)
ROLE_HIERARCHY = ['user', 'rag_user', 'agent_user', 'admin', 'owner']


def get_role_level(role: str) -> int:
    """Get role level in hierarchy"""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return 0


def has_min_role(user_role: str, min_role: str) -> bool:
    """Check if user role is at or above minimum required role"""
    return get_role_level(user_role) >= get_role_level(min_role)


async def get_current_user_role(request: Request) -> str:
    """
    Get current user's role from request.
    
    TODO: Integrate with actual auth middleware.
    For now, returns 'owner' for development.
    """
    # Check if user is attached to request by auth middleware
    user = getattr(request.state, 'user', None)
    if user and hasattr(user, 'role'):
        return user.role
    
    # Development fallback - remove in production
    return 'owner'


def require_role(*roles: str):
    """
    Dependency to require specific roles.
    
    Args:
        roles: List of allowed roles
    
    Usage:
        @router.get("/endpoint", dependencies=[require_role("admin")])
    """
    async def check_role(request: Request):
        user_role = await get_current_user_role(request)
        
        # Check if user has one of the required roles
        if user_role in roles:
            return user_role
        
        # Check if user's role is higher in hierarchy
        min_required_level = min(get_role_level(r) for r in roles)
        if get_role_level(user_role) >= min_required_level:
            return user_role
        
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Insufficient permissions",
                "required": list(roles),
                "current": user_role
            }
        )
    
    return Depends(check_role)


def require_min_role(min_role: str):
    """
    Dependency to require minimum role level.
    
    Args:
        min_role: Minimum role level required
    
    Usage:
        @router.get("/endpoint", dependencies=[require_min_role("agent_user")])
    """
    async def check_min_role(request: Request):
        user_role = await get_current_user_role(request)
        
        if has_min_role(user_role, min_role):
            return user_role
        
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Insufficient permissions",
                "required": min_role,
                "current": user_role
            }
        )
    
    return Depends(check_min_role)
