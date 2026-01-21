"""
SIEM Audit Log Exporter - Enterprise security event integration

Supports shipping structured audit logs to:
- Splunk HEC (HTTP Event Collector)
- Datadog Logs API
- Generic HTTP/HTTPS webhook

Usage:
    from app.siem_exporter import siem_logger, AuditEvent
    
    # Log a security event
    await siem_logger.log(AuditEvent(
        action="user.login",
        actor="user@example.com",
        resource="session",
        status="success",
        metadata={"ip": "192.168.1.1"}
    ))

Configuration (environment variables):
    SIEM_ENABLED=true
    SIEM_BACKEND=splunk|datadog|webhook
    SIEM_ENDPOINT=https://your-siem.example.com/...
    SIEM_TOKEN=your-auth-token
    SIEM_BATCH_SIZE=50
    SIEM_FLUSH_INTERVAL=5
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Standard audit actions for security events"""
    # Authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_MFA_ENABLED = "user.mfa_enabled"
    
    # Authorization
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PERMISSION_CHANGED = "permission.changed"
    
    # Data Access
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # Agent Actions
    AGENT_TOOL_CALLED = "agent.tool_called"
    AGENT_TOOL_APPROVED = "agent.tool_approved"
    AGENT_TOOL_DENIED = "agent.tool_denied"
    
    # RAG Actions
    RAG_INGEST = "rag.ingest"
    RAG_QUERY = "rag.query"
    RAG_DELETE = "rag.delete"
    
    # Admin Actions
    CONFIG_CHANGED = "config.changed"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    ROLE_ASSIGNED = "role.assigned"


@dataclass
class AuditEvent:
    """Structured audit event for SIEM export"""
    action: str  # AuditAction value or custom string
    actor: str  # User ID, email, or system identifier
    resource: str  # What was accessed/modified
    status: str = "success"  # success, failure, error
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = {
            "action": self.action,
            "actor": self.actor,
            "resource": self.resource,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "service": "beyondcloud",
        }
        
        # Add optional fields if present
        if self.trace_id:
            data["trace_id"] = self.trace_id
        if self.span_id:
            data["span_id"] = self.span_id
        if self.session_id:
            data["session_id"] = self.session_id
        if self.ip_address:
            data["ip_address"] = self.ip_address
        if self.user_agent:
            data["user_agent"] = self.user_agent
        if self.metadata:
            data["metadata"] = self.metadata
            
        return data


class SIEMExporter:
    """
    Base class for SIEM exporters.
    Handles batching, retry logic, and async export.
    """
    
    def __init__(
        self,
        endpoint: str,
        token: str,
        batch_size: int = 50,
        flush_interval: float = 5.0,
        max_retries: int = 3,
    ):
        self.endpoint = endpoint
        self.token = token
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        
        self._queue: List[AuditEvent] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        """Start the background flush task"""
        if self._running:
            return
        self._running = True
        self._client = httpx.AsyncClient(timeout=30.0)
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"SIEM exporter started: {self.__class__.__name__}")
    
    async def stop(self):
        """Stop the exporter and flush remaining events"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush()
        if self._client:
            await self._client.aclose()
        logger.info("SIEM exporter stopped")
    
    async def log(self, event: AuditEvent):
        """Queue an audit event for export"""
        async with self._lock:
            self._queue.append(event)
            if len(self._queue) >= self.batch_size:
                await self._flush()
    
    async def _flush_loop(self):
        """Background task to flush events periodically"""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            async with self._lock:
                if self._queue:
                    await self._flush()
    
    async def _flush(self):
        """Flush queued events to SIEM"""
        if not self._queue:
            return
        
        events = self._queue.copy()
        self._queue.clear()
        
        for attempt in range(self.max_retries):
            try:
                await self._send_batch(events)
                logger.debug(f"Flushed {len(events)} events to SIEM")
                return
            except Exception as e:
                logger.warning(f"SIEM export attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to export {len(events)} events after {self.max_retries} attempts")
    
    async def _send_batch(self, events: List[AuditEvent]):
        """Send a batch of events - override in subclasses"""
        raise NotImplementedError


class SplunkHECExporter(SIEMExporter):
    """Splunk HTTP Event Collector exporter"""
    
    async def _send_batch(self, events: List[AuditEvent]):
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        # Splunk HEC format: one JSON per line
        payload = "\n".join(
            json.dumps({
                "event": event.to_dict(),
                "sourcetype": "beyondcloud:audit",
                "source": "beyondcloud-api",
            })
            for event in events
        )
        
        response = await self._client.post(
            self.endpoint,
            content=payload,
            headers={
                "Authorization": f"Splunk {self.token}",
                "Content-Type": "application/json",
            }
        )
        response.raise_for_status()


class DatadogExporter(SIEMExporter):
    """Datadog Logs API exporter"""
    
    async def _send_batch(self, events: List[AuditEvent]):
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        # Datadog format
        payload = [
            {
                "message": json.dumps(event.to_dict()),
                "service": "beyondcloud",
                "ddsource": "python",
                "ddtags": f"action:{event.action},status:{event.status}",
            }
            for event in events
        ]
        
        response = await self._client.post(
            self.endpoint or "https://http-intake.logs.datadoghq.com/api/v2/logs",
            json=payload,
            headers={
                "DD-API-KEY": self.token,
                "Content-Type": "application/json",
            }
        )
        response.raise_for_status()


class WebhookExporter(SIEMExporter):
    """Generic webhook exporter for custom SIEM integrations"""
    
    async def _send_batch(self, events: List[AuditEvent]):
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        payload = {
            "events": [event.to_dict() for event in events],
            "batch_size": len(events),
            "source": "beyondcloud",
        }
        
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = await self._client.post(
            self.endpoint,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()


class NoOpExporter(SIEMExporter):
    """No-op exporter for when SIEM is disabled"""
    
    def __init__(self):
        self._queue = []
    
    async def start(self):
        pass
    
    async def stop(self):
        pass
    
    async def log(self, event: AuditEvent):
        # Just log locally for debugging
        logger.debug(f"Audit: {event.action} by {event.actor} on {event.resource}")
    
    async def _send_batch(self, events):
        pass


# =============================================================================
# Factory and Global Instance
# =============================================================================

_siem_logger: Optional[SIEMExporter] = None


def get_siem_logger() -> SIEMExporter:
    """
    Get or create the global SIEM logger instance.
    
    Configuration via environment:
        SIEM_ENABLED: true/false
        SIEM_BACKEND: splunk, datadog, webhook
        SIEM_ENDPOINT: SIEM API endpoint URL
        SIEM_TOKEN: Authentication token
        SIEM_BATCH_SIZE: Events per batch (default: 50)
        SIEM_FLUSH_INTERVAL: Seconds between flushes (default: 5)
    """
    global _siem_logger
    
    if _siem_logger is None:
        enabled = os.getenv("SIEM_ENABLED", "false").lower() == "true"
        
        if not enabled:
            _siem_logger = NoOpExporter()
            logger.info("SIEM export disabled (set SIEM_ENABLED=true to enable)")
            return _siem_logger
        
        backend = os.getenv("SIEM_BACKEND", "webhook").lower()
        endpoint = os.getenv("SIEM_ENDPOINT", "")
        token = os.getenv("SIEM_TOKEN", "")
        batch_size = int(os.getenv("SIEM_BATCH_SIZE", "50"))
        flush_interval = float(os.getenv("SIEM_FLUSH_INTERVAL", "5"))
        
        if not endpoint:
            logger.warning("SIEM_ENDPOINT not configured, using NoOp exporter")
            _siem_logger = NoOpExporter()
            return _siem_logger
        
        if backend == "splunk":
            _siem_logger = SplunkHECExporter(
                endpoint=endpoint,
                token=token,
                batch_size=batch_size,
                flush_interval=flush_interval,
            )
        elif backend == "datadog":
            _siem_logger = DatadogExporter(
                endpoint=endpoint,
                token=token,
                batch_size=batch_size,
                flush_interval=flush_interval,
            )
        else:
            _siem_logger = WebhookExporter(
                endpoint=endpoint,
                token=token,
                batch_size=batch_size,
                flush_interval=flush_interval,
            )
    
    return _siem_logger


# Convenience alias
siem_logger = get_siem_logger


async def audit_log(
    action: str,
    actor: str,
    resource: str,
    status: str = "success",
    **kwargs
):
    """Convenience function for logging audit events"""
    event = AuditEvent(
        action=action,
        actor=actor,
        resource=resource,
        status=status,
        **kwargs
    )
    await get_siem_logger().log(event)
