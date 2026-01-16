"""
OTel-Compatible Tracing Module

Provides a decorator-based API for tracing that stores to PostgreSQL
but follows OpenTelemetry data model for easy future migration.

Usage:
    from app.tracing import tracer, create_span

    with create_span("rag.retrieve", attributes={"query": q}):
        results = retrieve(q)

    # Or as decorator
    @tracer.span("rag.embed")
    async def embed_text(text: str):
        ...
"""
import uuid
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import wraps
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import json


@dataclass
class SpanEvent:
    """Event within a span"""
    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """OTel-compatible Span"""
    trace_id: str
    span_id: str
    name: str
    parent_span_id: Optional[str] = None
    kind: str = "INTERNAL"
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ns: Optional[int] = None
    status_code: str = "UNSET"
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    resource: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    
    def set_attribute(self, key: str, value: Any):
        """Add an attribute to the span"""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span"""
        self.events.append(SpanEvent(name=name, attributes=attributes or {}))
    
    def set_status(self, code: str, message: Optional[str] = None):
        """Set span status (OK, ERROR, UNSET)"""
        self.status_code = code
        self.status_message = message
    
    def end(self):
        """End the span and calculate duration"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ns = int((self.end_time - self.start_time).total_seconds() * 1e9)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ns": self.duration_ns,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": [{"name": e.name, "timestamp": e.timestamp.isoformat(), "attributes": e.attributes} for e in self.events],
            "resource": self.resource,
            "user_id": self.user_id,
        }


def generate_trace_id() -> str:
    """Generate 32-character hex trace ID (128-bit)"""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate 16-character hex span ID (64-bit)"""
    return uuid.uuid4().hex[:16]


class Tracer:
    """
    OTel-compatible tracer that stores to PostgreSQL
    
    Future migration to OpenTelemetry:
        Replace tracer.start_span() with otel_tracer.start_as_current_span()
    """
    
    def __init__(self, service_name: str = "ai-service"):
        self.service_name = service_name
        self.service_version = "1.0.0"
        self._current_span: Optional[Span] = None
        self._spans_to_export: List[Span] = []
    
    @property
    def current_span(self) -> Optional[Span]:
        return self._current_span
    
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Span:
        """Start a new span"""
        span = Span(
            trace_id=trace_id or generate_trace_id(),
            span_id=generate_span_id(),
            name=name,
            parent_span_id=parent_span_id or (self._current_span.span_id if self._current_span else None),
            attributes=attributes or {},
            user_id=user_id,
            resource={
                "service.name": self.service_name,
                "service.version": self.service_version,
            }
        )
        self._current_span = span
        return span
    
    def end_span(self, span: Span):
        """End a span and queue for export"""
        span.end()
        self._spans_to_export.append(span)
        if self._current_span == span:
            self._current_span = None
    
    def get_pending_spans(self) -> List[Span]:
        """Get spans waiting to be exported"""
        spans = self._spans_to_export.copy()
        self._spans_to_export.clear()
        return spans
    
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Decorator for tracing a function"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span = self.start_span(name, attributes)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.set_status("ERROR", str(e))
                    raise
                finally:
                    self.end_span(span)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span = self.start_span(name, attributes)
                try:
                    result = func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.set_status("ERROR", str(e))
                    raise
                finally:
                    self.end_span(span)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator


# Global tracer instance
tracer = Tracer(service_name="beyondcloud-ai")


@asynccontextmanager
async def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
):
    """
    Context manager for creating spans
    
    Usage:
        async with create_span("rag.retrieve", {"query": q}) as span:
            results = await retrieve(q)
            span.set_attribute("result_count", len(results))
    """
    span = tracer.start_span(name, attributes, user_id=user_id)
    try:
        yield span
        span.set_status("OK")
    except Exception as e:
        span.set_status("ERROR", str(e))
        raise
    finally:
        tracer.end_span(span)


async def export_spans_to_db(db_session):
    """Export pending spans to PostgreSQL"""
    from sqlalchemy import text
    
    spans = tracer.get_pending_spans()
    if not spans:
        return
    
    for span in spans:
        await db_session.execute(
            text("""
                INSERT INTO traces 
                (trace_id, span_id, parent_span_id, name, kind, start_time, end_time, 
                 duration_ns, status_code, status_message, attributes, events, resource, user_id)
                VALUES 
                (:trace_id, :span_id, :parent_span_id, :name, :kind, :start_time, :end_time,
                 :duration_ns, :status_code, :status_message, :attributes, :events, :resource, :user_id)
            """),
            {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "name": span.name,
                "kind": span.kind,
                "start_time": span.start_time,  # Pass datetime object directly
                "end_time": span.end_time,      # Pass datetime object directly
                "duration_ns": span.duration_ns,
                "status_code": span.status_code,
                "status_message": span.status_message,
                "attributes": json.dumps(span.attributes),
                "events": json.dumps([{"name": e.name, "timestamp": e.timestamp.isoformat(), "attributes": e.attributes} for e in span.events]),
                "resource": json.dumps(span.resource),
                "user_id": span.user_id,
            }
        )
    
    await db_session.commit()

