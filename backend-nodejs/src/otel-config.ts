/**
 * OpenTelemetry Configuration - Enterprise observability for Node.js
 *
 * Provides:
 * - Automatic Express instrumentation
 * - OTLP export to Jaeger/Honeycomb/Datadog
 * - Context propagation
 * - Custom span creation
 *
 * Usage:
 *   // MUST be imported first, before other modules
 *   import { setupOtel, getTracer } from './otel-config';
 *   setupOtel();
 *
 *   // Create custom spans
 *   const tracer = getTracer('my-module');
 *   const span = tracer.startSpan('my_operation');
 *   span.setAttribute('user_id', userId);
 *   span.end();
 *
 * Configuration:
 *   OTEL_ENABLED=true
 *   OTEL_SERVICE_NAME=beyondcloud-api
 *   OTEL_EXPORTER=otlp|console
 *   OTEL_ENDPOINT=http://localhost:4317
 *   OTEL_HEADERS=x-honeycomb-team=your-key
 */

// Types for when OTel is not installed
interface Span {
    setAttribute(key: string, value: string | number | boolean): void;
    setStatus(status: { code: number; message?: string }): void;
    addEvent(name: string, attributes?: Record<string, any>): void;
    end(): void;
}

interface Tracer {
    startSpan(name: string, options?: any): Span;
}

let _otelAvailable = false;
let _api: any = null;
let _sdk: any = null;

// Try to import OpenTelemetry packages
async function loadOtel() {
    try {
        _api = await import('@opentelemetry/api');
        const { NodeTracerProvider } = await import('@opentelemetry/sdk-trace-node');
        const { BatchSpanProcessor, ConsoleSpanExporter } = await import('@opentelemetry/sdk-trace-base');
        const { Resource } = await import('@opentelemetry/resources');
        const { SEMRESATTRS_SERVICE_NAME, SEMRESATTRS_SERVICE_VERSION } = await import('@opentelemetry/semantic-conventions');
        const { OTLPTraceExporter } = await import('@opentelemetry/exporter-trace-otlp-grpc');
        const { ExpressInstrumentation } = await import('@opentelemetry/instrumentation-express');
        const { HttpInstrumentation } = await import('@opentelemetry/instrumentation-http');
        const { registerInstrumentations } = await import('@opentelemetry/instrumentation');

        _sdk = {
            NodeTracerProvider,
            BatchSpanProcessor,
            ConsoleSpanExporter,
            Resource,
            SEMRESATTRS_SERVICE_NAME,
            SEMRESATTRS_SERVICE_VERSION,
            OTLPTraceExporter,
            ExpressInstrumentation,
            HttpInstrumentation,
            registerInstrumentations,
        };
        _otelAvailable = true;
        return true;
    } catch (error) {
        console.warn('OpenTelemetry packages not installed. Install with:');
        console.warn('npm install @opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-grpc @opentelemetry/instrumentation-express @opentelemetry/instrumentation-http');
        return false;
    }
}

/**
 * Setup OpenTelemetry tracing
 * MUST be called before importing Express or other instrumented modules
 */
export async function setupOtel(serviceName?: string, serviceVersion: string = '1.0.0'): Promise<boolean> {
    const enabled = process.env.OTEL_ENABLED?.toLowerCase() === 'true';
    if (!enabled) {
        console.log('OpenTelemetry disabled (set OTEL_ENABLED=true to enable)');
        return false;
    }

    const loaded = await loadOtel();
    if (!loaded) {
        return false;
    }

    const name = serviceName || process.env.OTEL_SERVICE_NAME || 'beyondcloud-api';
    const environment = process.env.NODE_ENV || 'development';

    // Create resource
    const resource = new _sdk.Resource({
        [_sdk.SEMRESATTRS_SERVICE_NAME]: name,
        [_sdk.SEMRESATTRS_SERVICE_VERSION]: serviceVersion,
        'deployment.environment': environment,
    });

    // Create provider
    const provider = new _sdk.NodeTracerProvider({ resource });

    // Configure exporter
    const exporterType = process.env.OTEL_EXPORTER?.toLowerCase() || 'otlp';

    if (exporterType === 'console') {
        provider.addSpanProcessor(new _sdk.BatchSpanProcessor(new _sdk.ConsoleSpanExporter()));
        console.log('Using Console span exporter');
    } else {
        const endpoint = process.env.OTEL_ENDPOINT || 'http://localhost:4317';
        const headers = parseHeaders(process.env.OTEL_HEADERS || '');

        const exporter = new _sdk.OTLPTraceExporter({
            url: endpoint,
            headers,
        });
        provider.addSpanProcessor(new _sdk.BatchSpanProcessor(exporter));
        console.log(`Using OTLP exporter: ${endpoint}`);
    }

    // Register provider
    provider.register();

    // Auto-instrument Express and HTTP
    _sdk.registerInstrumentations({
        instrumentations: [
            new _sdk.HttpInstrumentation(),
            new _sdk.ExpressInstrumentation(),
        ],
    });

    console.log(`OpenTelemetry initialized for ${name}`);
    return true;
}

function parseHeaders(headersStr: string): Record<string, string> {
    if (!headersStr) return {};

    const headers: Record<string, string> = {};
    for (const item of headersStr.split(',')) {
        const [key, value] = item.split('=');
        if (key && value) {
            headers[key.trim()] = value.trim();
        }
    }
    return headers;
}

/**
 * Get a tracer instance for creating custom spans
 */
export function getTracer(name: string = 'beyondcloud'): Tracer {
    if (!_otelAvailable || !_api) {
        return new NoOpTracer();
    }
    return _api.trace.getTracer(name);
}

/**
 * Get the current active span
 */
export function getCurrentSpan(): Span | undefined {
    if (!_otelAvailable || !_api) {
        return undefined;
    }
    return _api.trace.getActiveSpan();
}

/**
 * Get trace context for correlation
 */
export function getTraceContext(): { trace_id?: string; span_id?: string } {
    if (!_otelAvailable || !_api) {
        return {};
    }

    const span = _api.trace.getActiveSpan();
    if (!span) return {};

    const ctx = span.spanContext();
    return {
        trace_id: ctx.traceId,
        span_id: ctx.spanId,
    };
}

// No-op implementations for when OTel is not available
class NoOpSpan implements Span {
    setAttribute(_key: string, _value: string | number | boolean): void { }
    setStatus(_status: { code: number; message?: string }): void { }
    addEvent(_name: string, _attributes?: Record<string, any>): void { }
    end(): void { }
}

class NoOpTracer implements Tracer {
    startSpan(_name: string, _options?: any): Span {
        return new NoOpSpan();
    }
}

/**
 * Decorator-style function for tracing async operations
 */
export function traced<T>(
    name: string,
    fn: () => Promise<T>,
    attributes?: Record<string, string | number | boolean>
): Promise<T> {
    const tracer = getTracer();
    const span = tracer.startSpan(name);

    if (attributes) {
        for (const [key, value] of Object.entries(attributes)) {
            span.setAttribute(key, value);
        }
    }

    return fn()
        .then((result) => {
            span.end();
            return result;
        })
        .catch((error) => {
            span.setAttribute('error', true);
            span.setAttribute('error.message', error.message);
            span.end();
            throw error;
        });
}
