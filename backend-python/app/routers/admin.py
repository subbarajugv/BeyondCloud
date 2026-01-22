"""
Admin Router - API endpoints for admin dashboard functionality
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user_id
from app.role_check import require_min_role, UserWithRole

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ========== Schemas ==========

class UserSummary(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    role: str
    created_at: str


class UserRoleUpdate(BaseModel):
    role: str


class TicketCreate(BaseModel):
    subject: str
    description: str


class TicketResponse(BaseModel):
    id: str
    user_id: str
    subject: str
    description: str
    status: str
    created_at: str
    resolved_at: Optional[str] = None


class AdminStats(BaseModel):
    total_users: int
    total_documents: int
    total_collections: int
    open_tickets: int
    guardrail_violations_7d: int


# ========== Admin Endpoints ==========

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(require_min_role("admin")),
):
    """Get admin dashboard statistics"""
    
    # Count users
    result = await db.execute(text("SELECT COUNT(*) FROM users"))
    total_users = result.scalar() or 0
    
    # Count documents
    result = await db.execute(text("SELECT COUNT(*) FROM rag_sources"))
    total_documents = result.scalar() or 0
    
    # Count collections
    result = await db.execute(text("SELECT COUNT(*) FROM rag_collections"))
    total_collections = result.scalar() or 0
    
    # Count open tickets
    result = await db.execute(
        text("SELECT COUNT(*) FROM support_tickets WHERE status != 'resolved'")
    )
    open_tickets = result.scalar() or 0
    
    # Count guardrail violations (last 7 days)
    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM guardrail_violations 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
    )
    guardrail_violations_7d = result.scalar() or 0
    
    return AdminStats(
        total_users=total_users,
        total_documents=total_documents,
        total_collections=total_collections,
        open_tickets=open_tickets,
        guardrail_violations_7d=guardrail_violations_7d,
    )


@router.get("/users", response_model=List[UserSummary])
async def list_users(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(require_min_role("admin")),
):
    """List all users (admin only)"""
    result = await db.execute(
        text("""
            SELECT id, email, display_name, role, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset}
    )
    
    return [
        UserSummary(
            id=str(row.id),
            email=row.email,
            display_name=row.display_name,
            role=row.role or "user",
            created_at=row.created_at.isoformat(),
        )
        for row in result.fetchall()
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: UserWithRole = Depends(require_min_role("admin")),
):
    """Update a user's role (admin only)"""
    valid_roles = ["user", "rag_user", "agent_user", "admin"]
    if update.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")
    
    result = await db.execute(
        text("UPDATE users SET role = :role WHERE id = :user_id RETURNING id"),
        {"role": update.role, "user_id": user_id}
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(404, "User not found")
    
    return {"message": f"User role updated to {update.role}", "user_id": user_id}


# ========== Support Tickets ==========

@router.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(require_min_role("admin")),
):
    """List support tickets (admin only)"""
    query = """
        SELECT id, user_id, subject, description, status, created_at, resolved_at
        FROM support_tickets
    """
    params = {"limit": limit}
    
    if status:
        query += " WHERE status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC LIMIT :limit"
    
    result = await db.execute(text(query), params)
    
    return [
        TicketResponse(
            id=str(row.id),
            user_id=str(row.user_id),
            subject=row.subject,
            description=row.description,
            status=row.status,
            created_at=row.created_at.isoformat(),
            resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
        )
        for row in result.fetchall()
    ]


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserWithRole = Depends(require_min_role("admin")),
):
    """Mark a ticket as resolved (admin only)"""
    result = await db.execute(
        text("""
            UPDATE support_tickets 
            SET status = 'resolved', resolved_at = NOW()
            WHERE id = :ticket_id
            RETURNING id
        """),
        {"ticket_id": ticket_id}
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(404, "Ticket not found")
    
    return {"message": "Ticket resolved", "ticket_id": ticket_id}


# ========== User Ticket Endpoints ==========

@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    ticket: TicketCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a support ticket (any authenticated user)"""
    import uuid
    
    ticket_id = str(uuid.uuid4())
    
    await db.execute(
        text("""
            INSERT INTO support_tickets (id, user_id, subject, description, status)
            VALUES (:id, :user_id, :subject, :description, 'open')
        """),
        {
            "id": ticket_id,
            "user_id": user_id,
            "subject": ticket.subject,
            "description": ticket.description,
        }
    )
    await db.commit()
    
    # Fetch the created ticket
    result = await db.execute(
        text("SELECT * FROM support_tickets WHERE id = :id"),
        {"id": ticket_id}
    )
    row = result.fetchone()
    
    return TicketResponse(
        id=str(row.id),
        user_id=str(row.user_id),
        subject=row.subject,
        description=row.description,
        status=row.status,
        created_at=row.created_at.isoformat(),
        resolved_at=None,
    )


@router.get("/my-tickets", response_model=List[TicketResponse])
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get current user's tickets"""
    result = await db.execute(
        text("""
            SELECT id, user_id, subject, description, status, created_at, resolved_at
            FROM support_tickets
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": user_id}
    )
    
    return [
        TicketResponse(
            id=str(row.id),
            user_id=str(row.user_id),
            subject=row.subject,
            description=row.description,
            status=row.status,
            created_at=row.created_at.isoformat(),
            resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
        )
        for row in result.fetchall()
    ]


# ========== GDPR Endpoints ==========

from fastapi.responses import Response
from app.services.gdpr_service import delete_user_data, export_user_data


@router.delete("/users/{user_id}/data")
async def gdpr_delete_user_data(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: UserWithRole = Depends(require_min_role("admin")),
):
    """
    GDPR Right to Erasure - Delete all user data.
    
    Permanently deletes:
    - RAG sources and chunks
    - Collections
    - Usage statistics
    - Support tickets
    - Traces
    - Guardrail violations
    - Settings
    
    Note: Does NOT delete the user account itself (handle via separate endpoint).
    """
    # Verify user exists
    result = await db.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    if not result.fetchone():
        raise HTTPException(404, "User not found")
    
    # Delete all user data
    deletion_result = await delete_user_data(db, user_id)
    
    return {
        "message": "User data deleted successfully",
        **deletion_result
    }


@router.get("/users/{user_id}/export")
async def gdpr_export_user_data(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: UserWithRole = Depends(require_min_role("admin")),
):
    """
    GDPR Right to Portability - Export all user data as ZIP.
    
    Exports:
    - User profile
    - RAG sources and chunks
    - Collections
    - Usage statistics
    - Support tickets
    - Settings
    
    Returns: ZIP file download
    """
    # Verify user exists
    result = await db.execute(
        text("SELECT id, email FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    user = result.fetchone()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Generate export
    zip_bytes = await export_user_data(db, user_id)
    
    # Return as downloadable ZIP
    filename = f"beyondcloud_export_{user.email}_{user_id[:8]}.zip"
    
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/my-data/export")
async def gdpr_export_own_data(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    GDPR Right to Portability - Export your own data as ZIP.
    
    Any authenticated user can export their own data.
    """
    # Generate export
    zip_bytes = await export_user_data(db, user_id)
    
    # Return as downloadable ZIP
    filename = f"beyondcloud_export_{user_id[:8]}.zip"
    
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("/my-data")
async def gdpr_delete_own_data(
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    GDPR Right to Erasure - Delete your own data.
    
    Any authenticated user can delete their own data.
    Requires confirm=true query parameter.
    
    Note: Does NOT delete your account, only your data.
    """
    if not confirm:
        raise HTTPException(
            400, 
            "Must confirm deletion by passing confirm=true. This action is irreversible."
        )
    
    # Delete all user data
    deletion_result = await delete_user_data(db, user_id)
    
    return {
        "message": "Your data has been deleted successfully",
        **deletion_result
    }
