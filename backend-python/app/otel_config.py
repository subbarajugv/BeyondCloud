"""
OpenTelemetry Configuration - Enterprise observability

Provides:
- Automatic FastAPI instrumentation
- OTLP export to Jaeger/Honeycomb/Datadog
- Context propagation
- Custom span creation

Usage:
    from app.otel_config import setup_otel, get_tracer
    
    # In main.py startup
    setup_otel(app)
    
    # Create custom spans
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("user_id", user_id)
        # ... do work

Configuration (environment variables):
    OTEL_ENABLED=true
    OTEL_SERVICE_NAME=beyondcloud-api
    OTEL_EXPORTER=otlp|jaeger|console
    OTEL_ENDPOINT=http://localhost:4317 (for OTLP)
    OTEL_HEADERS=x-honeycomb-team=your-key (for Honeycomb)
"""
import os
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Check if OpenTelemetry is available
_otel_available = False
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    _otel_available = True
except ImportError:
    logger.warning("OpenTelemetry packages not installed. Run: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp")


def setup_otel(app=None, service_name: str = None, service_version: str = "1.0.0"):
    """
    Setup OpenTelemetry tracing.
    
    Args:
        app: FastAPI application instance (for auto-instrumentation)
        service_name: Service name for traces (default: OTEL_SERVICE_NAME or "beyondcloud-api")
        service_version: Service version for traces
    """
    if not _otel_available:
        logger.warning("OpenTelemetry not available, skipping setup")
        return
    
    enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
        return
    
    # Service info
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "beyondcloud-api")
    
    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure exporter based on environment
    exporter_type = os.getenv("OTEL_EXPORTER", "otlp").lower()
    
    if exporter_type == "console":
        # Console exporter for development/debugging
        exporter = ConsoleSpanExporter()
        logger.info("Using Console span exporter")
    else:
        # OTLP exporter (works with Jaeger, Honeycomb, Datadog, etc.)
        endpoint = os.getenv("OTEL_ENDPOINT", "http://localhost:4317")
        headers = _parse_headers(os.getenv("OTEL_HEADERS", ""))
        
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers,
            insecure=endpoint.startswith("http://"),
        )
        logger.info(f"Using OTLP exporter: {endpoint}")
    
    # Add batch processor for efficiency
    provider.add_span_processor(BatchSpanProcessor(exporter))
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Auto-instrument FastAPI if app provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumented with OpenTelemetry")
    
    logger.info(f"OpenTelemetry initialized for {service_name}")


def _parse_headers(headers_str: str) -> dict:
    """Parse headers from comma-separated key=value string"""
    if not headers_str:
        return {}
    
    headers = {}
    for item in headers_str.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating custom spans.
    
    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("operation") as span:
            span.set_attribute("key", "value")
    """
    if not _otel_available:
        return _NoOpTracer()
    
    return trace.get_tracer(name)


def get_current_span():
    """Get the current active span"""
    if not _otel_available:
        return _NoOpSpan()
    return trace.get_current_span()


def get_trace_context() -> dict:
    """
    Get current trace context for correlation.
    Returns dict with trace_id and span_id if available.
    """
    if not _otel_available:
        return {}
    
    span = trace.get_current_span()
    ctx = span.get_span_context()
    
    if ctx.is_valid:
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    return {}


class _NoOpSpan:
    """No-op span for when OTel is not available"""
    def set_attribute(self, key, value): pass
    def set_status(self, status): pass
    def add_event(self, name, attributes=None): pass
    def end(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


class _NoOpTracer:
    """No-op tracer for when OTel is not available"""
    @contextmanager
    def start_as_current_span(self, name, **kwargs):
        yield _NoOpSpan()
    
    def start_span(self, name, **kwargs):
        return _NoOpSpan()


# =============================================================================
# Convenience decorators
# =============================================================================

def traced(name: str = None, attributes: dict = None):
    """
    Decorator to trace a function.
    
    Usage:
        @traced("my_function")
        async def my_function():
            ...
    """
    def decorator(func):
        import functools
        import asyncio
        
        span_name = name or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                    raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
