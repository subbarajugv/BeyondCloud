"""
Agent Spawner - RBAC-enabled agent instance creation and governance.

This module handles:
- Template visibility checks
- Permission intersection
- Spawn limits (depth, concurrent instances)
- Ancestry tracking for self-spawning agents
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from copy import deepcopy
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.role_check import UserWithRole, has_min_role, has_any_role
from app.schemas.agent_spawning import (
    AgentSpec,
    SpawnPolicy,
    EffectivePermissions,
    AgentEventCreate
)
from app.logging_config import get_logger

logger = get_logger(__name__)


# Default spawn governance limits
DEFAULT_SPAWN_POLICY = SpawnPolicy(
    max_depth=3,
    max_total_instances=50,
    max_children_per_agent=10
)

# Platform-level tool restrictions by role
ROLE_TOOL_PERMISSIONS = {
    "user": ["rag_retrieve", "calculator"],
    "rag_user": ["rag_retrieve", "rag_ingest", "calculator"],
    "agent_user": ["rag_retrieve", "rag_ingest", "calculator", "search_web", "read_url", "python_repl"],
    "admin": ["rag_retrieve", "rag_ingest", "calculator", "search_web", "read_url", "python_repl", "list_dir", "read_file", "write_file"],
    "owner": ["*"]  # All tools
}


class SpawnPermissionError(Exception):
    """Raised when spawn permission is denied."""
    pass


class SpawnLimitExceededError(Exception):
    """Raised when spawn limits are exceeded."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when template is not found or not accessible."""
    pass


class AgentSpawner:
    """
    RBAC-enabled agent instance spawner.
    
    Responsibilities:
    - Load and validate templates
    - Check visibility and role requirements
    - Compute effective permissions via intersection
    - Enforce spawn governance (depth, limits)
    - Create instances with isolated context
    """
    
    def __init__(self, db: AsyncSession, user: UserWithRole):
        self.db = db
        self.user = user
        self.spawn_policy = DEFAULT_SPAWN_POLICY
    
    async def spawn(
        self,
        template_id: UUID,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        parent_instance_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Spawn a new agent instance from a template.
        
        Args:
            template_id: UUID of the template to spawn from
            task: The task/objective for the agent
            context: Optional initial context (will be deep-copied)
            parent_instance_id: If this is a child agent, the parent's ID
            
        Returns:
            Created instance record
            
        Raises:
            TemplateNotFoundError: Template doesn't exist or not visible
            SpawnPermissionError: User lacks required role
            SpawnLimitExceededError: Spawn limits exceeded
        """
        # 1. Load template
        template = await self._load_template(template_id)
        if not template:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        
        # 2. Check visibility
        if not self._can_access_template(template):
            logger.warning(f"User {self.user.id} denied access to template {template_id}")
            raise TemplateNotFoundError(f"Template {template_id} not accessible")
        
        # 3. Check role requirements
        required_roles = template.get("required_roles", [])
        if required_roles and not has_any_role(self.user.role, required_roles):
            logger.warning(
                f"User {self.user.id} (role: {self.user.role}) lacks required roles: {required_roles}"
            )
            raise SpawnPermissionError(
                f"Insufficient role. Required: {required_roles}, Current: {self.user.role}"
            )
        
        # 4. Get parent instance for ancestry tracking
        parent_instance = None
        depth = 0
        root_instance_id = None
        
        if parent_instance_id:
            parent_instance = await self._load_instance(parent_instance_id)
            if parent_instance:
                depth = parent_instance["depth"] + 1
                root_instance_id = parent_instance.get("root_instance_id") or parent_instance["id"]
        
        # 5. Check depth limit
        if depth >= self.spawn_policy.max_depth:
            raise SpawnLimitExceededError(
                f"Max spawn depth ({self.spawn_policy.max_depth}) exceeded"
            )
        
        # 6. Check concurrent instance limit
        active_count = await self._count_active_instances()
        if active_count >= self.spawn_policy.max_total_instances:
            raise SpawnLimitExceededError(
                f"Max concurrent instances ({self.spawn_policy.max_total_instances}) exceeded"
            )
        
        # 7. Compute effective permissions
        effective_perms = self._compute_effective_permissions(template)
        
        # 8. Create instance with isolated context
        instance_id = await self._create_instance(
            template_id=template_id,
            template_version=template["version"],
            task=task,
            context=deepcopy(context) if context else {},
            depth=depth,
            parent_instance_id=parent_instance_id,
            root_instance_id=root_instance_id,
            effective_permissions=effective_perms
        )
        
        # 9. Log spawn event
        await self._log_event(
            instance_id=instance_id,
            event_type="spawned",
            payload={
                "template_id": str(template_id),
                "template_name": template["name"],
                "effective_tools": effective_perms.tools,
                "effective_models": effective_perms.models,
                "depth": depth
            }
        )
        
        logger.info(
            f"Spawned instance {instance_id} from template {template['name']} "
            f"for user {self.user.id} (depth: {depth})"
        )
        
        return {"id": instance_id, "status": "queued", "depth": depth}
    
    async def _load_template(self, template_id: UUID) -> Optional[Dict[str, Any]]:
        """Load template from database."""
        result = await self.db.execute(
            text("""
                SELECT id, name, description, owner_id, org_id, scope, spec, version,
                       required_roles, max_template_tools, icon, color, is_active
                FROM agent_templates
                WHERE id = :template_id AND is_active = true
            """),
            {"template_id": str(template_id)}
        )
        row = result.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "owner_id": row[3],
            "org_id": row[4],
            "scope": row[5],
            "spec": row[6],
            "version": row[7],
            "required_roles": row[8] or [],
            "max_template_tools": row[9] or [],
            "icon": row[10],
            "color": row[11]
        }
    
    def _can_access_template(self, template: Dict[str, Any]) -> bool:
        """Check if user can access template based on scope."""
        scope = template["scope"]
        owner_id = str(template["owner_id"])
        org_id = template.get("org_id")
        
        # Personal templates: only owner
        if scope == "personal":
            return str(self.user.id) == owner_id
        
        # Org templates: same org (when we have org_id on users)
        # For now, admins can access org templates
        if scope == "org":
            return has_min_role(self.user.role, "admin")
        
        # Global templates: everyone
        if scope == "global":
            return True
        
        return False
    
    def _compute_effective_permissions(self, template: Dict[str, Any]) -> EffectivePermissions:
        """
        Compute effective permissions via intersection.
        
        effective = template ∩ user_role ∩ platform
        """
        spec = template["spec"]
        template_tools = set(spec.get("allowed_tools", []))
        template_models = set(spec.get("allowed_models", []))
        
        # Get user's allowed tools based on role
        user_tools = set(ROLE_TOOL_PERMISSIONS.get(self.user.role, []))
        if "*" in user_tools:
            user_tools = template_tools  # Owner gets all template tools
        
        # Intersection
        effective_tools = list(template_tools & user_tools)
        effective_models = list(template_models)  # No model restrictions for now
        
        # Min of max_steps
        template_max_steps = spec.get("max_steps", 10)
        role_max_steps = 20 if has_min_role(self.user.role, "admin") else 10
        effective_max_steps = min(template_max_steps, role_max_steps)
        
        # Token budget based on role
        token_budgets = {
            "user": 50000,
            "rag_user": 100000,
            "agent_user": 200000,
            "admin": 500000,
            "owner": 1000000
        }
        token_budget = token_budgets.get(self.user.role, 50000)
        
        return EffectivePermissions(
            tools=effective_tools,
            models=effective_models,
            max_steps=effective_max_steps,
            token_budget=token_budget
        )
    
    async def _count_active_instances(self) -> int:
        """Count active instances for current user."""
        result = await self.db.execute(
            text("""
                SELECT COUNT(*) FROM agent_instances
                WHERE spawned_by_user_id = :user_id
                AND status IN ('queued', 'running')
            """),
            {"user_id": self.user.id}
        )
        return result.scalar() or 0
    
    async def _load_instance(self, instance_id: UUID) -> Optional[Dict[str, Any]]:
        """Load instance from database."""
        result = await self.db.execute(
            text("""
                SELECT id, depth, root_instance_id, spawned_by_user_id
                FROM agent_instances
                WHERE id = :instance_id
            """),
            {"instance_id": str(instance_id)}
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "depth": row[1],
            "root_instance_id": row[2],
            "spawned_by_user_id": row[3]
        }
    
    async def _create_instance(
        self,
        template_id: UUID,
        template_version: int,
        task: str,
        context: Dict[str, Any],
        depth: int,
        parent_instance_id: Optional[UUID],
        root_instance_id: Optional[UUID],
        effective_permissions: EffectivePermissions
    ) -> UUID:
        """Create instance in database."""
        import json
        
        # Include effective permissions in context
        context["_effective_permissions"] = {
            "tools": effective_permissions.tools,
            "models": effective_permissions.models,
            "max_steps": effective_permissions.max_steps,
            "token_budget": effective_permissions.token_budget
        }
        
        result = await self.db.execute(
            text("""
                INSERT INTO agent_instances (
                    template_id, template_version, spawned_by_user_id,
                    parent_instance_id, root_instance_id, depth,
                    task, context, status, current_state
                ) VALUES (
                    :template_id, :template_version, :user_id,
                    :parent_id, :root_id, :depth,
                    :task, :context::jsonb, 'queued', 'init'
                )
                RETURNING id
            """),
            {
                "template_id": str(template_id),
                "template_version": template_version,
                "user_id": self.user.id,
                "parent_id": str(parent_instance_id) if parent_instance_id else None,
                "root_id": str(root_instance_id) if root_instance_id else None,
                "depth": depth,
                "task": task,
                "context": json.dumps(context)
            }
        )
        await self.db.commit()
        return result.scalar()
    
    async def _log_event(
        self,
        instance_id: UUID,
        event_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """Log an event for the instance."""
        import json
        
        await self.db.execute(
            text("""
                INSERT INTO agent_events (instance_id, event_type, payload)
                VALUES (:instance_id, :event_type, :payload::jsonb)
            """),
            {
                "instance_id": str(instance_id),
                "event_type": event_type,
                "payload": json.dumps(payload)
            }
        )
        await self.db.commit()
