"""
Database Log Handler - Push logs to PostgreSQL session_logs table

Usage:
    from app.logging_config import setup_logging
    from app.db_log_handler import add_db_handler
    
    setup_logging()
    add_db_handler()  # Adds async DB logging
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from queue import Queue
import threading


class AsyncDBHandler(logging.Handler):
    """
    Async logging handler that writes to PostgreSQL session_logs table.
    
    Uses a queue and background thread to avoid blocking the main event loop.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_level: int = logging.INFO,
    ):
        super().__init__(level=min_level)
        self.session_id = session_id
        self.user_id = user_id
        self.queue: Queue = Queue(maxsize=1000)  # Buffer up to 1000 logs
        self._running = True
        self._thread = threading.Thread(target=self._consumer, daemon=True)
        self._thread.start()
    
    def emit(self, record: logging.LogRecord):
        """Queue log record for async processing"""
        if not self._running:
            return
        
        try:
            log_entry = self._format_record(record)
            self.queue.put_nowait(log_entry)
        except Exception:
            self.handleError(record)
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record for database insertion"""
        # Extract trace context if available
        trace_id = None
        span_id = None
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")
        except (ImportError, Exception):
            pass
        
        # Build log entry
        entry = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "level": record.levelname,
            "action": record.name,  # Logger name as action
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
            "created_at": datetime.utcnow(),
        }
        
        # Add extra fields
        if hasattr(record, "endpoint"):
            entry["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            entry["method"] = record.method
        if hasattr(record, "status_code"):
            entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            entry["duration_ms"] = record.duration_ms
        if hasattr(record, "metadata"):
            entry["metadata"] = record.metadata
        
        # Add error info
        if record.exc_info:
            entry["error"] = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
        
        return entry
    
    def _consumer(self):
        """Background thread that writes logs to database"""
        batch = []
        batch_size = 50
        flush_interval = 5.0  # Flush every 5 seconds
        
        import time
        last_flush = time.time()
        
        while self._running or not self.queue.empty():
            try:
                # Get from queue with timeout
                try:
                    entry = self.queue.get(timeout=1.0)
                    batch.append(entry)
                except Exception:
                    pass
                
                # Flush if batch is full or interval passed
                now = time.time()
                if len(batch) >= batch_size or (batch and now - last_flush > flush_interval):
                    self._flush_batch(batch)
                    batch = []
                    last_flush = now
                    
            except Exception as e:
                logging.getLogger(__name__).warning(f"DB logging error: {e}")
        
        # Final flush on shutdown
        if batch:
            self._flush_batch(batch)
    
    def _flush_batch(self, batch: list):
        """Write batch of logs to database"""
        if not batch:
            return
        
        try:
            # Run async insert in a new event loop (we're in a thread)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._insert_logs(batch))
            finally:
                loop.close()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to flush logs to DB: {e}")
    
    async def _insert_logs(self, batch: list):
        """Insert logs into database"""
        from app.database import get_db_context
        from sqlalchemy import text
        import json
        
        async with get_db_context() as db:
            for entry in batch:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO session_logs 
                            (session_id, user_id, level, action, message, trace_id, span_id,
                             endpoint, method, status_code, duration_ms, metadata, error, created_at)
                            VALUES (:session_id, :user_id, :level, :action, :message, :trace_id, :span_id,
                                    :endpoint, :method, :status_code, :duration_ms, :metadata, :error, :created_at)
                        """),
                        {
                            "session_id": entry.get("session_id"),
                            "user_id": entry.get("user_id"),
                            "level": entry.get("level", "INFO"),
                            "action": entry.get("action", "unknown")[:100],
                            "message": entry.get("message", "")[:1000],  # Truncate long messages
                            "trace_id": entry.get("trace_id"),
                            "span_id": entry.get("span_id"),
                            "endpoint": entry.get("endpoint"),
                            "method": entry.get("method"),
                            "status_code": entry.get("status_code"),
                            "duration_ms": entry.get("duration_ms"),
                            "metadata": json.dumps(entry.get("metadata")) if entry.get("metadata") else None,
                            "error": entry.get("error"),
                            "created_at": entry.get("created_at"),
                        }
                    )
                except Exception as e:
                    logging.getLogger(__name__).debug(f"Failed to insert log: {e}")
            
            await db.commit()
    
    def close(self):
        """Shutdown handler gracefully"""
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=10.0)
        super().close()


# Global handler instance
_db_handler: Optional[AsyncDBHandler] = None


def add_db_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    min_level: int = logging.INFO,
):
    """Add database logging handler to root logger"""
    global _db_handler
    
    if _db_handler:
        return  # Already added
    
    _db_handler = AsyncDBHandler(
        session_id=session_id,
        user_id=user_id,
        min_level=min_level,
    )
    
    logging.getLogger().addHandler(_db_handler)


def set_session_context(session_id: str, user_id: str):
    """Update the current session context for logging"""
    global _db_handler
    if _db_handler:
        _db_handler.session_id = session_id
        _db_handler.user_id = user_id
