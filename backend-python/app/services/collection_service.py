"""
Collection Service - Hierarchical RAG collections with RBAC

Supports:
- Nested folders (unlimited depth via parent_id)
- Visibility: public, role, team, private, personal
- RBAC integration with allowed_roles, allowed_teams, allowed_users
"""
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CollectionService:
    """Service for managing RAG collections (folders)"""
    
    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        visibility: str = "personal",
        allowed_roles: Optional[List[str]] = None,
        allowed_teams: Optional[List[str]] = None,
        allowed_users: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new collection"""
        collection_id = str(uuid.uuid4())
        
        result = await db.execute(
            text("""
                INSERT INTO rag_collections 
                (id, parent_id, user_id, name, description, visibility, allowed_roles, allowed_teams, allowed_users)
                VALUES (:id, :parent_id, :user_id, :name, :description, :visibility, :allowed_roles, :allowed_teams, :allowed_users)
                RETURNING id, parent_id, user_id, name, description, visibility, created_at
            """),
            {
                "id": collection_id,
                "parent_id": parent_id,
                "user_id": user_id,
                "name": name,
                "description": description,
                "visibility": visibility,
                "allowed_roles": allowed_roles or [],
                "allowed_teams": allowed_teams or [],
                "allowed_users": allowed_users or [],
            }
        )
        await db.commit()
        
        row = result.fetchone()
        return {
            "id": str(row.id),
            "parent_id": str(row.parent_id) if row.parent_id else None,
            "user_id": str(row.user_id),
            "name": row.name,
            "description": row.description,
            "visibility": row.visibility,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    
    async def list_accessible(
        self,
        db: AsyncSession,
        user_id: str,
        user_roles: Optional[List[str]] = None,
        user_teams: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all collections accessible to the user.
        
        Access rules:
        - 'public': all users
        - 'role': users with matching roles
        - 'team': users in matching teams
        - 'private': users in allowed_users list
        - 'personal': only the owner
        """
        user_roles = user_roles or []
        user_teams = user_teams or []
        
        result = await db.execute(
            text("""
                SELECT c.id, c.parent_id, c.user_id, c.name, c.description, 
                       c.visibility, c.created_at,
                       (c.user_id = :user_id) as is_owner,
                       COUNT(DISTINCT s.id) as source_count
                FROM rag_collections c
                LEFT JOIN rag_sources s ON s.collection_id = c.id
                WHERE c.visibility = 'public'
                   OR c.user_id = :user_id
                   OR (c.visibility = 'role' AND c.allowed_roles && :user_roles)
                   OR (c.visibility = 'team' AND c.allowed_teams && :user_teams)
                   OR (c.visibility = 'private' AND :user_id = ANY(c.allowed_users))
                GROUP BY c.id
                ORDER BY c.name
            """),
            {
                "user_id": user_id,
                "user_roles": user_roles,
                "user_teams": [uuid.UUID(t) if isinstance(t, str) else t for t in user_teams] if user_teams else [],
            }
        )
        
        collections = []
        for row in result.fetchall():
            collections.append({
                "id": str(row.id),
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "user_id": str(row.user_id),
                "name": row.name,
                "description": row.description,
                "visibility": row.visibility,
                "is_owner": row.is_owner,
                "source_count": row.source_count,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })
        
        return collections
    
    async def list_tree(
        self,
        db: AsyncSession,
        user_id: str,
        user_roles: Optional[List[str]] = None,
        user_teams: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List collections as a nested tree structure.
        """
        flat_list = await self.list_accessible(db, user_id, user_roles, user_teams)
        
        # Build tree
        by_id = {c["id"]: {**c, "children": []} for c in flat_list}
        roots = []
        
        for c in flat_list:
            if c["parent_id"] and c["parent_id"] in by_id:
                by_id[c["parent_id"]]["children"].append(by_id[c["id"]])
            else:
                roots.append(by_id[c["id"]])
        
        return roots
    
    async def get(
        self,
        db: AsyncSession,
        collection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a single collection by ID"""
        result = await db.execute(
            text("""
                SELECT id, parent_id, user_id, name, description, visibility,
                       allowed_roles, allowed_teams, allowed_users, created_at
                FROM rag_collections
                WHERE id = :id
            """),
            {"id": collection_id}
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        return {
            "id": str(row.id),
            "parent_id": str(row.parent_id) if row.parent_id else None,
            "user_id": str(row.user_id),
            "name": row.name,
            "description": row.description,
            "visibility": row.visibility,
            "allowed_roles": list(row.allowed_roles) if row.allowed_roles else [],
            "allowed_teams": [str(t) for t in row.allowed_teams] if row.allowed_teams else [],
            "allowed_users": [str(u) for u in row.allowed_users] if row.allowed_users else [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    
    async def update(
        self,
        db: AsyncSession,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        visibility: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None,
        allowed_teams: Optional[List[str]] = None,
        allowed_users: Optional[List[str]] = None,
    ) -> bool:
        """Update a collection"""
        updates = []
        params = {"id": collection_id}
        
        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        if description is not None:
            updates.append("description = :description")
            params["description"] = description
        if visibility is not None:
            updates.append("visibility = :visibility")
            params["visibility"] = visibility
        if allowed_roles is not None:
            updates.append("allowed_roles = :allowed_roles")
            params["allowed_roles"] = allowed_roles
        if allowed_teams is not None:
            updates.append("allowed_teams = :allowed_teams")
            params["allowed_teams"] = allowed_teams
        if allowed_users is not None:
            updates.append("allowed_users = :allowed_users")
            params["allowed_users"] = allowed_users
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        
        result = await db.execute(
            text(f"UPDATE rag_collections SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        await db.commit()
        
        return result.rowcount > 0
    
    async def delete(
        self,
        db: AsyncSession,
        collection_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a collection (cascades to child collections and sources).
        Only owner can delete.
        """
        result = await db.execute(
            text("""
                DELETE FROM rag_collections 
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": collection_id, "user_id": user_id}
        )
        await db.commit()
        
        return result.rowcount > 0
    
    async def move(
        self,
        db: AsyncSession,
        collection_id: str,
        new_parent_id: Optional[str],
    ) -> bool:
        """Move a collection to a new parent"""
        # Prevent circular references
        if new_parent_id:
            # Check if new_parent is a descendant of collection_id
            result = await db.execute(
                text("""
                    WITH RECURSIVE ancestors AS (
                        SELECT id, parent_id FROM rag_collections WHERE id = :new_parent_id
                        UNION ALL
                        SELECT c.id, c.parent_id FROM rag_collections c
                        JOIN ancestors a ON c.id = a.parent_id
                    )
                    SELECT 1 FROM ancestors WHERE id = :collection_id
                """),
                {"new_parent_id": new_parent_id, "collection_id": collection_id}
            )
            if result.fetchone():
                raise ValueError("Cannot move collection: would create circular reference")
        
        result = await db.execute(
            text("UPDATE rag_collections SET parent_id = :parent_id, updated_at = NOW() WHERE id = :id"),
            {"id": collection_id, "parent_id": new_parent_id}
        )
        await db.commit()
        
        return result.rowcount > 0


# Singleton service instance
collection_service = CollectionService()
