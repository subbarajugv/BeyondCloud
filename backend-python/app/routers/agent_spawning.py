"""
Agent Spawning API - REST endpoints for agent templates and instances.

Provides:
- Template CRUD (create, list, get, update, delete)
- Instance spawning and status
- Real-time event streaming via SSE
"""
from typing import List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.role_check import (
    UserWithRole, 
    require_min_role, 
    require_agent_user,
    get_current_user_with_role,
    has_min_role
)
from app.schemas.agent_spawning import (
    AgentTemplateCreate,
    AgentTemplateUpdate,
    AgentTemplateResponse,
    SpawnRequest,
    InstanceStatusResponse,
    InstanceResultResponse,
    AgentEventResponse
)
from app.services.agent_spawner import (
    AgentSpawner,
    SpawnPermissionError,
    SpawnLimitExceededError,
    TemplateNotFoundError
)
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agent Spawning"])


# ============================================================
# TEMPLATE ENDPOINTS
# ============================================================

@router.post("/templates", response_model=AgentTemplateResponse, status_code=201)
async def create_template(
    template: AgentTemplateCreate,
    user: UserWithRole = Depends(require_min_role("agent_user")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new agent template.
    
    Requires: agent_user role or higher
    
    Scope rules:
    - agent_user can create 'personal' templates
    - admin can create 'org' templates
    - owner can create 'global' templates
    """
    # Validate scope permissions
    if template.scope == "org" and not has_min_role(user.role, "admin"):
        raise HTTPException(403, "Only admins can create org-scoped templates")
    if template.scope == "global" and not has_min_role(user.role, "owner"):
        raise HTTPException(403, "Only owners can create global templates")
    
    # Insert template
    result = await db.execute(
        text("""
            INSERT INTO agent_templates (
                name, description, owner_id, scope, spec, 
                required_roles, icon, color
            ) VALUES (
                :name, :description, :owner_id, :scope, :spec::jsonb,
                :required_roles, :icon, :color
            )
            RETURNING id, name, description, owner_id, org_id, scope, spec, version,
                      required_roles, icon, color, is_active, created_at, updated_at
        """),
        {
            "name": template.name,
            "description": template.description,
            "owner_id": user.id,
            "scope": template.scope,
            "spec": template.spec.model_dump_json(),
            "required_roles": template.required_roles,
            "icon": template.icon,
            "color": template.color
        }
    )
    await db.commit()
    
    row = result.fetchone()
    return _row_to_template_response(row)


@router.get("/templates", response_model=List[AgentTemplateResponse])
async def list_templates(
    scope: Optional[str] = Query(None, description="Filter by scope: personal, org, global"),
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    List agent templates visible to the current user.
    
    Returns:
    - All personal templates owned by user
    - All org templates (if admin)
    - All global templates
    """
    # Build visibility filter
    visibility_conditions = ["(scope = 'global')"]
    params = {"user_id": user.id}
    
    # Personal templates
    visibility_conditions.append("(scope = 'personal' AND owner_id = :user_id)")
    
    # Org templates for admins
    if has_min_role(user.role, "admin"):
        visibility_conditions.append("(scope = 'org')")
    
    where_clause = " OR ".join(visibility_conditions)
    
    # Optional scope filter
    if scope:
        where_clause = f"({where_clause}) AND scope = :scope"
        params["scope"] = scope
    
    result = await db.execute(
        text(f"""
            SELECT id, name, description, owner_id, org_id, scope, spec, version,
                   required_roles, icon, color, is_active, created_at, updated_at
            FROM agent_templates
            WHERE is_active = true AND ({where_clause})
            ORDER BY created_at DESC
        """),
        params
    )
    
    rows = result.fetchall()
    return [_row_to_template_response(row) for row in rows]


@router.get("/templates/{template_id}", response_model=AgentTemplateResponse)
async def get_template(
    template_id: UUID,
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific agent template."""
    result = await db.execute(
        text("""
            SELECT id, name, description, owner_id, org_id, scope, spec, version,
                   required_roles, icon, color, is_active, created_at, updated_at
            FROM agent_templates
            WHERE id = :template_id
        """),
        {"template_id": str(template_id)}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    
    template = _row_to_template_response(row)
    
    # Check visibility
    if template.scope == "personal" and str(template.owner_id) != user.id:
        raise HTTPException(404, "Template not found")
    if template.scope == "org" and not has_min_role(user.role, "admin"):
        raise HTTPException(404, "Template not found")
    
    return template


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an agent template (soft delete).
    
    Only the owner or admins can delete templates.
    """
    # Get template
    result = await db.execute(
        text("SELECT owner_id, scope FROM agent_templates WHERE id = :id"),
        {"id": str(template_id)}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(404, "Template not found")
    
    owner_id, scope = row
    
    # Check permissions
    can_delete = (
        str(owner_id) == user.id or
        has_min_role(user.role, "admin")
    )
    
    if not can_delete:
        raise HTTPException(403, "Cannot delete this template")
    
    # Soft delete
    await db.execute(
        text("UPDATE agent_templates SET is_active = false WHERE id = :id"),
        {"id": str(template_id)}
    )
    await db.commit()


# ============================================================
# INSTANCE ENDPOINTS
# ============================================================

@router.post("/templates/{template_id}/spawn", response_model=InstanceStatusResponse)
async def spawn_instance(
    template_id: UUID,
    request: SpawnRequest,
    user: UserWithRole = Depends(require_agent_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Spawn a new agent instance from a template.
    
    Requires: agent_user role or higher
    
    Permissions are computed at spawn time via intersection.
    """
    spawner = AgentSpawner(db, user)
    
    try:
        result = await spawner.spawn(
            template_id=template_id,
            task=request.task,
            context=request.context
        )
        
        # Fetch full instance
        return await _get_instance_status(db, result["id"], user)
        
    except TemplateNotFoundError as e:
        raise HTTPException(404, str(e))
    except SpawnPermissionError as e:
        raise HTTPException(403, str(e))
    except SpawnLimitExceededError as e:
        raise HTTPException(429, str(e))


@router.get("/instances", response_model=List[InstanceStatusResponse])
async def list_instances(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, le=100),
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """List agent instances for current user."""
    params = {"user_id": user.id, "limit": limit}
    
    status_filter = ""
    if status:
        status_filter = "AND status = :status"
        params["status"] = status
    
    result = await db.execute(
        text(f"""
            SELECT id, template_id, template_version, spawned_by_user_id,
                   parent_instance_id, root_instance_id, depth, status,
                   current_state, step, task, tokens_used, cost_usd, error,
                   created_at, updated_at, completed_at
            FROM agent_instances
            WHERE spawned_by_user_id = :user_id {status_filter}
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        params
    )
    
    return [_row_to_instance_response(row) for row in result.fetchall()]


@router.get("/instances/{instance_id}", response_model=InstanceStatusResponse)
async def get_instance_status(
    instance_id: UUID,
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """Get instance status."""
    return await _get_instance_status(db, instance_id, user)


@router.post("/instances/{instance_id}/cancel", status_code=204)
async def cancel_instance(
    instance_id: UUID,
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running instance.
    
    Can be cancelled by:
    - Instance owner
    - Admin or higher
    """
    instance = await _get_instance_status(db, instance_id, user)
    
    can_cancel = (
        str(instance.spawned_by_user_id) == user.id or
        has_min_role(user.role, "admin")
    )
    
    if not can_cancel:
        raise HTTPException(403, "Cannot cancel this instance")
    
    if instance.status not in ("queued", "running"):
        raise HTTPException(400, f"Cannot cancel instance with status: {instance.status}")
    
    await db.execute(
        text("""
            UPDATE agent_instances 
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = :id
        """),
        {"id": str(instance_id)}
    )
    await db.commit()


@router.get("/instances/{instance_id}/events", response_model=List[AgentEventResponse])
async def get_instance_events(
    instance_id: UUID,
    user: UserWithRole = Depends(get_current_user_with_role),
    db: AsyncSession = Depends(get_db)
):
    """Get events for an instance."""
    # Verify access
    await _get_instance_status(db, instance_id, user)
    
    result = await db.execute(
        text("""
            SELECT id, instance_id, event_type, payload, trace_id, span_id,
                   tokens_used, latency_ms, timestamp
            FROM agent_events
            WHERE instance_id = :instance_id
            ORDER BY timestamp ASC
        """),
        {"instance_id": str(instance_id)}
    )
    
    return [_row_to_event_response(row) for row in result.fetchall()]


# ============================================================
# HELPERS
# ============================================================

def _row_to_template_response(row) -> AgentTemplateResponse:
    """Convert DB row to AgentTemplateResponse."""
    from app.schemas.agent_spawning import AgentSpec
    
    spec_data = row[6] if isinstance(row[6], dict) else json.loads(row[6])
    
    return AgentTemplateResponse(
        id=row[0],
        name=row[1],
        description=row[2],
        owner_id=row[3],
        org_id=row[4],
        scope=row[5],
        spec=AgentSpec(**spec_data),
        version=row[7],
        required_roles=row[8] or [],
        icon=row[9],
        color=row[10],
        is_active=row[11],
        created_at=row[12],
        updated_at=row[13]
    )


def _row_to_instance_response(row) -> InstanceStatusResponse:
    """Convert DB row to InstanceStatusResponse."""
    return InstanceStatusResponse(
        id=row[0],
        template_id=row[1],
        template_version=row[2],
        spawned_by_user_id=row[3],
        parent_instance_id=row[4],
        root_instance_id=row[5],
        depth=row[6],
        status=row[7],
        current_state=row[8],
        step=row[9],
        task=row[10],
        tokens_used=row[11] or 0,
        cost_usd=float(row[12] or 0),
        error=row[13],
        created_at=row[14],
        updated_at=row[15],
        completed_at=row[16]
    )


def _row_to_event_response(row) -> AgentEventResponse:
    """Convert DB row to AgentEventResponse."""
    return AgentEventResponse(
        id=row[0],
        instance_id=row[1],
        event_type=row[2],
        payload=row[3] or {},
        trace_id=row[4],
        span_id=row[5],
        tokens_used=row[6] or 0,
        latency_ms=row[7],
        timestamp=row[8]
    )


async def _get_instance_status(
    db: AsyncSession, 
    instance_id: UUID, 
    user: UserWithRole
) -> InstanceStatusResponse:
    """Get instance status with access check."""
    result = await db.execute(
        text("""
            SELECT id, template_id, template_version, spawned_by_user_id,
                   parent_instance_id, root_instance_id, depth, status,
                   current_state, step, task, tokens_used, cost_usd, error,
                   created_at, updated_at, completed_at
            FROM agent_instances
            WHERE id = :instance_id
        """),
        {"instance_id": str(instance_id)}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")
    
    instance = _row_to_instance_response(row)
    
    # Check access: owner or admin
    can_access = (
        str(instance.spawned_by_user_id) == user.id or
        has_min_role(user.role, "admin")
    )
    
    if not can_access:
        raise HTTPException(404, "Instance not found")
    
    return instance
