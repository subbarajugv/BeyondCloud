"""
GDPR Service - Data erasure and portability endpoints

Implements:
- Right to Erasure: Delete all user data
- Right to Portability: Export all user data as ZIP
"""
import io
import json
import zipfile
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.tracing import create_span


async def delete_user_data(db: AsyncSession, user_id: str) -> dict:
    """
    Delete all data associated with a user (GDPR Right to Erasure).
    
    Deletes:
    - RAG sources and chunks
    - RAG collections
    - Usage stats
    - Support tickets
    - Traces
    - Guardrail violations
    - RAG settings
    
    Returns:
        Summary of deleted records
    """
    async with create_span("gdpr.delete_user_data", {"user_id": user_id}) as span:
        deleted_counts = {}
        
        # Delete RAG chunks (via cascade from sources, but explicit for count)
        result = await db.execute(
            text("""
                DELETE FROM rag_chunks 
                WHERE source_id IN (SELECT id FROM rag_sources WHERE user_id = :user_id)
                RETURNING id
            """),
            {"user_id": user_id}
        )
        deleted_counts["rag_chunks"] = result.rowcount
        
        # Delete RAG sources
        result = await db.execute(
            text("DELETE FROM rag_sources WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        deleted_counts["rag_sources"] = result.rowcount
        
        # Delete RAG collections
        result = await db.execute(
            text("DELETE FROM rag_collections WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        deleted_counts["rag_collections"] = result.rowcount
        
        # Delete usage stats
        result = await db.execute(
            text("DELETE FROM usage_stats WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        deleted_counts["usage_stats"] = result.rowcount
        
        # Delete support tickets
        result = await db.execute(
            text("DELETE FROM support_tickets WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        deleted_counts["support_tickets"] = result.rowcount
        
        # Delete traces
        result = await db.execute(
            text("DELETE FROM traces WHERE user_id = :user_id RETURNING span_id"),
            {"user_id": user_id}
        )
        deleted_counts["traces"] = result.rowcount
        
        # Delete guardrail violations
        result = await db.execute(
            text("DELETE FROM guardrail_violations WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        deleted_counts["guardrail_violations"] = result.rowcount
        
        # Delete RAG settings
        result = await db.execute(
            text("DELETE FROM rag_settings WHERE user_id = :user_id RETURNING user_id"),
            {"user_id": user_id}
        )
        deleted_counts["rag_settings"] = result.rowcount
        
        await db.commit()
        
        total_deleted = sum(deleted_counts.values())
        span.set_attribute("total_deleted", total_deleted)
        
        return {
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_counts": deleted_counts,
            "total_records_deleted": total_deleted
        }


async def export_user_data(db: AsyncSession, user_id: str) -> bytes:
    """
    Export all user data as a ZIP file (GDPR Right to Portability).
    
    Exports:
    - User profile (from users table)
    - RAG sources and chunks
    - Collections
    - Usage statistics
    - Support tickets
    - Settings
    
    Returns:
        ZIP file as bytes
    """
    async with create_span("gdpr.export_user_data", {"user_id": user_id}) as span:
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
        }
        
        # Get user profile
        result = await db.execute(
            text("SELECT id, email, display_name, role, created_at FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        if row:
            export_data["profile"] = {
                "id": str(row.id),
                "email": row.email,
                "display_name": row.display_name,
                "role": row.role,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
        
        # Get RAG sources
        result = await db.execute(
            text("""
                SELECT id, name, type, visibility, metadata, created_at, chunk_count
                FROM rag_sources WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        export_data["rag_sources"] = [
            {
                "id": str(row.id),
                "name": row.name,
                "type": row.type,
                "visibility": row.visibility,
                "metadata": row.metadata,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "chunk_count": row.chunk_count
            }
            for row in result.fetchall()
        ]
        
        # Get RAG chunks (content only, not embeddings)
        result = await db.execute(
            text("""
                SELECT c.id, c.source_id, c.content, c.chunk_index, c.metadata, c.created_at
                FROM rag_chunks c
                JOIN rag_sources s ON c.source_id = s.id
                WHERE s.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        export_data["rag_chunks"] = [
            {
                "id": str(row.id),
                "source_id": str(row.source_id),
                "content": row.content,
                "chunk_index": row.chunk_index,
                "metadata": row.metadata,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in result.fetchall()
        ]
        
        # Get collections
        result = await db.execute(
            text("""
                SELECT id, name, description, parent_id, visibility, created_at
                FROM rag_collections WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        export_data["collections"] = [
            {
                "id": str(row.id),
                "name": row.name,
                "description": row.description,
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "visibility": row.visibility,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in result.fetchall()
        ]
        
        # Get usage stats
        result = await db.execute(
            text("SELECT * FROM usage_stats WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        export_data["usage_stats"] = [
            {k: (v.isoformat() if hasattr(v, 'isoformat') else str(v) if k == 'id' else v)
             for k, v in dict(row._mapping).items()}
            for row in result.fetchall()
        ]
        
        # Get support tickets
        result = await db.execute(
            text("SELECT * FROM support_tickets WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        export_data["support_tickets"] = [
            {k: (v.isoformat() if hasattr(v, 'isoformat') else str(v) if k in ('id', 'user_id') else v)
             for k, v in dict(row._mapping).items()}
            for row in result.fetchall()
        ]
        
        # Get RAG settings
        result = await db.execute(
            text("SELECT * FROM rag_settings WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        if row:
            export_data["rag_settings"] = {
                k: (v.isoformat() if hasattr(v, 'isoformat') else str(v) if k == 'user_id' else v)
                for k, v in dict(row._mapping).items()
            }
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Main data JSON
            zf.writestr(
                "user_data.json",
                json.dumps(export_data, indent=2, default=str)
            )
            
            # Individual files for large data
            if export_data.get("rag_sources"):
                zf.writestr(
                    "rag_sources.json",
                    json.dumps(export_data["rag_sources"], indent=2, default=str)
                )
            
            if export_data.get("rag_chunks"):
                zf.writestr(
                    "rag_chunks.json", 
                    json.dumps(export_data["rag_chunks"], indent=2, default=str)
                )
            
            # README
            zf.writestr("README.txt", f"""BeyondCloud Data Export
========================
Export Date: {export_data['export_timestamp']}
User ID: {user_id}

This archive contains all data associated with your account.

Files:
- user_data.json: Complete export of all your data
- rag_sources.json: Your uploaded documents (if any)
- rag_chunks.json: Document chunks with content (if any)

For questions about this export, contact support.
""")
        
        zip_buffer.seek(0)
        span.set_attribute("export_size_bytes", len(zip_buffer.getvalue()))
        
        return zip_buffer.getvalue()
