"""
Role-Based Access Control utilities for Python backend

Mirrors the Node.js RBAC system to ensure consistent role enforcement.
Role hierarchy: user < rag_user < agent_user < admin < owner
"""
from typing import Optional, List
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.auth import get_current_user, User
from app.logging_config import get_logger

logger = get_logger(__name__)

# Role hierarchy (higher index = more permissions)
ROLE_HIERARCHY = ['user', 'rag_user', 'agent_user', 'admin', 'owner']


def get_role_level(role: str) -> int:
    """Get role level in hierarchy"""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return 0  # Default to lowest level if unknown role


def has_min_role(user_role: str, min_role: str) -> bool:
    """Check if user role is at or above minimum required role"""
    return get_role_level(user_role) >= get_role_level(min_role)


def has_any_role(user_role: str, roles: List[str]) -> bool:
    """Check if user has one of the specified roles or higher"""
    if user_role in roles:
        return True
    # Check if user's role is higher than any required role
    min_required_level = min(get_role_level(r) for r in roles)
    return get_role_level(user_role) >= min_required_level


@dataclass
class UserWithRole:
    """User with role information fetched from database"""
    id: str
    email: str
    role: str


async def get_user_role(
    db: AsyncSession,
    user_id: str
) -> str:
    """Fetch user role from database"""
    result = await db.execute(
        text("SELECT role FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    row = result.fetchone()
    return row[0] if row else 'user'


async def get_current_user_with_role(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWithRole:
    """
    FastAPI dependency to get current user with their role from database.
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user: UserWithRole = Depends(get_current_user_with_role)):
            if not has_min_role(user.role, 'admin'):
                raise HTTPException(403, "Admin required")
    """
    role = await get_user_role(db, user.id)
    return UserWithRole(id=user.id, email=user.email, role=role)


def require_role(*roles: str):
    """
    Create a dependency that requires specific roles.
    
    Usage:
        @router.post("/admin-action")
        async def admin_action(
            user: UserWithRole = Depends(require_role('admin', 'owner'))
        ):
            ...
    """
    async def dependency(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserWithRole:
        role = await get_user_role(db, user.id)
        user_with_role = UserWithRole(id=user.id, email=user.email, role=role)
        
        if not has_any_role(role, list(roles)):
            logger.warning(f"Access denied for user {user.id}: requires {roles}, has {role}")
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Insufficient permissions",
                    "required": list(roles),
                    "current": role
                }
            )
        
        return user_with_role
    
    return dependency


def require_min_role(min_role: str):
    """
    Create a dependency that requires minimum role level.
    
    Usage:
        @router.post("/rag-admin")
        async def rag_admin(
            user: UserWithRole = Depends(require_min_role('admin'))
        ):
            ...
    """
    async def dependency(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserWithRole:
        role = await get_user_role(db, user.id)
        user_with_role = UserWithRole(id=user.id, email=user.email, role=role)
        
        if not has_min_role(role, min_role):
            logger.warning(f"Access denied for user {user.id}: requires min {min_role}, has {role}")
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN", 
                    "message": "Insufficient permissions",
                    "required": min_role,
                    "current": role
                }
            )
        
        return user_with_role
    
    return dependency


# Convenience dependencies for common role checks
require_admin = require_min_role('admin')
require_rag_user = require_min_role('rag_user')
require_agent_user = require_min_role('agent_user')
