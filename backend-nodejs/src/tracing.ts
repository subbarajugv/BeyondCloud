/**
 * OTel-Compatible Custom Tracing Module
 * 
 * Provides a custom tracing implementation that follows the OpenTelemetry data model.
 * Designed for easy migration to real OTel - just swap imports.
 * 
 * Usage:
 *     import { tracer, withSpan, createSpan } from './tracing';
 * 
 *     // Using withSpan helper
 *     const result = await withSpan('user.authenticate', async (span) => {
 *         span.setAttribute('user.id', userId);
 *         return await authenticateUser(userId);
 *     });
 * 
 *     // Using createSpan for more control
 *     const span = createSpan('db.query', { table: 'users' });
 *     try {
 *         const result = await db.query(...);
 *         span.setStatus('OK');
 *     } catch (e) {
 *         span.setStatus('ERROR', e.message);
 *     } finally {
 *         span.end();
 *     }
 * 
 * Future OTel migration:
 *     import { trace } from '@opentelemetry/api';
 *     const tracer = trace.getTracer('beyondcloud-nodejs');
 */

import { randomUUID } from 'crypto';

// ============================================================================
// Types & Interfaces (OTel-compatible)
// ============================================================================

export interface SpanEvent {
    name: string;
    timestamp: Date;
    attributes: Record<string, unknown>;
}

export type SpanStatus = 'UNSET' | 'OK' | 'ERROR';
export type SpanKind = 'INTERNAL' | 'SERVER' | 'CLIENT' | 'PRODUCER' | 'CONSUMER';

export interface SpanContext {
    traceId: string;
    spanId: string;
    parentSpanId?: string;
}

export interface SpanData {
    traceId: string;
    spanId: string;
    parentSpanId?: string;
    name: string;
    kind: SpanKind;
    startTime: Date;
    endTime?: Date;
    durationNs?: number;
    statusCode: SpanStatus;
    statusMessage?: string;
    attributes: Record<string, unknown>;
    events: SpanEvent[];
    resource: Record<string, unknown>;
    userId?: string;
}

// ============================================================================
// Span Class
// ============================================================================

export class Span {
    readonly traceId: string;
    readonly spanId: string;
    readonly parentSpanId?: string;
    readonly name: string;
    readonly kind: SpanKind;
    readonly startTime: Date;

    private endTime?: Date;
    private durationNs?: number;
    private statusCode: SpanStatus = 'UNSET';
    private statusMessage?: string;
    private attributes: Record<string, unknown> = {};
    private events: SpanEvent[] = [];
    private resource: Record<string, unknown>;
    private userId?: string;

    constructor(
        name: string,
        options: {
            traceId?: string;
            parentSpanId?: string;
            kind?: SpanKind;
            attributes?: Record<string, unknown>;
            userId?: string;
            resource?: Record<string, unknown>;
        } = {}
    ) {
        this.traceId = options.traceId || generateTraceId();
        this.spanId = generateSpanId();
        this.parentSpanId = options.parentSpanId;
        this.name = name;
        this.kind = options.kind || 'INTERNAL';
        this.startTime = new Date();
        this.attributes = options.attributes || {};
        this.userId = options.userId;
        this.resource = options.resource || {};
    }

    /**
     * Add an attribute to the span
     */
    setAttribute(key: string, value: unknown): this {
        this.attributes[key] = value;
        return this;
    }

    /**
     * Add multiple attributes
     */
    setAttributes(attributes: Record<string, unknown>): this {
        Object.assign(this.attributes, attributes);
        return this;
    }

    /**
     * Add an event to the span
     */
    addEvent(name: string, attributes?: Record<string, unknown>): this {
        this.events.push({
            name,
            timestamp: new Date(),
            attributes: attributes || {},
        });
        return this;
    }

    /**
     * Set span status (OK, ERROR, UNSET)
     */
    setStatus(code: SpanStatus, message?: string): this {
        this.statusCode = code;
        this.statusMessage = message;
        return this;
    }

    /**
     * Record an exception
     */
    recordException(error: Error): this {
        this.addEvent('exception', {
            'exception.type': error.name,
            'exception.message': error.message,
            'exception.stacktrace': error.stack,
        });
        return this;
    }

    /**
     * End the span and calculate duration
     */
    end(): void {
        if (this.endTime) return; // Already ended

        this.endTime = new Date();
        this.durationNs = (this.endTime.getTime() - this.startTime.getTime()) * 1_000_000;
    }

    /**
     * Check if span has ended
     */
    isEnded(): boolean {
        return this.endTime !== undefined;
    }

    /**
     * Get span context for propagation
     */
    getContext(): SpanContext {
        return {
            traceId: this.traceId,
            spanId: this.spanId,
            parentSpanId: this.parentSpanId,
        };
    }

    /**
     * Convert to dictionary for storage/export
     */
    toJSON(): SpanData {
        return {
            traceId: this.traceId,
            spanId: this.spanId,
            parentSpanId: this.parentSpanId,
            name: this.name,
            kind: this.kind,
            startTime: this.startTime,
            endTime: this.endTime,
            durationNs: this.durationNs,
            statusCode: this.statusCode,
            statusMessage: this.statusMessage,
            attributes: this.attributes,
            events: this.events,
            resource: this.resource,
            userId: this.userId,
        };
    }
}

// ============================================================================
// ID Generation (OTel-compatible format)
// ============================================================================

/**
 * Generate 32-character hex trace ID (128-bit)
 */
function generateTraceId(): string {
    return randomUUID().replace(/-/g, '');
}

/**
 * Generate 16-character hex span ID (64-bit)
 */
function generateSpanId(): string {
    return randomUUID().replace(/-/g, '').substring(0, 16);
}

// ============================================================================
// Tracer Class
// ============================================================================

export type SpanExporter = (span: Span) => void | Promise<void>;

export class Tracer {
    readonly serviceName: string;
    readonly serviceVersion: string;

    private currentSpan?: Span;
    private spanBuffer: Span[] = [];
    private exporters: SpanExporter[] = [];

    constructor(serviceName: string = 'beyondcloud-nodejs', serviceVersion: string = '1.0.0') {
        this.serviceName = serviceName;
        this.serviceVersion = serviceVersion;
    }

    /**
     * Get the currently active span
     */
    getCurrentSpan(): Span | undefined {
        return this.currentSpan;
    }

    /**
     * Start a new span
     */
    startSpan(
        name: string,
        options: {
            attributes?: Record<string, unknown>;
            kind?: SpanKind;
            parentSpan?: Span;
            userId?: string;
        } = {}
    ): Span {
        const parentSpanId = options.parentSpan?.spanId || this.currentSpan?.spanId;
        const traceId = options.parentSpan?.traceId || this.currentSpan?.traceId;

        const span = new Span(name, {
            traceId,
            parentSpanId,
            kind: options.kind,
            attributes: options.attributes,
            userId: options.userId,
            resource: {
                'service.name': this.serviceName,
                'service.version': this.serviceVersion,
            },
        });

        this.currentSpan = span;
        return span;
    }

    /**
     * End a span and queue for export
     */
    endSpan(span: Span): void {
        span.end();
        this.spanBuffer.push(span);

        if (this.currentSpan === span) {
            this.currentSpan = undefined;
        }

        // Export immediately to all exporters
        this.exporters.forEach(exporter => {
            try {
                exporter(span);
            } catch (e) {
                console.error('[Tracing] Export error:', e);
            }
        });
    }

    /**
     * Add a span exporter
     */
    addExporter(exporter: SpanExporter): void {
        this.exporters.push(exporter);
    }

    /**
     * Get and clear buffered spans
     */
    flushSpans(): Span[] {
        const spans = [...this.spanBuffer];
        this.spanBuffer = [];
        return spans;
    }
}

// ============================================================================
// Global Tracer Instance
// ============================================================================

const serviceName = process.env.OTEL_SERVICE_NAME || 'beyondcloud-nodejs';
const serviceVersion = process.env.npm_package_version || '1.0.0';

export const tracer = new Tracer(serviceName, serviceVersion);

// ============================================================================
// Console Exporter (for development)
// ============================================================================

const consoleExporter: SpanExporter = (span) => {
    const data = span.toJSON();
    const duration = data.durationNs ? (data.durationNs / 1_000_000).toFixed(2) : '?';
    const status = data.statusCode === 'ERROR' ? '❌' : data.statusCode === 'OK' ? '✅' : '⚪';

    console.log(
        `[Trace] ${status} ${data.name} (${duration}ms) ` +
        `trace=${data.traceId.substring(0, 8)} span=${data.spanId}`
    );

    if (data.statusCode === 'ERROR' && data.statusMessage) {
        console.log(`        └─ Error: ${data.statusMessage}`);
    }

    if (Object.keys(data.attributes).length > 0) {
        console.log(`        └─ Attrs: ${JSON.stringify(data.attributes)}`);
    }
};

// Enable console exporter in development
if (process.env.NODE_ENV !== 'production' || process.env.OTEL_TRACE_CONSOLE === 'true') {
    tracer.addExporter(consoleExporter);
    console.log(`[Tracing] Console exporter enabled for service: ${serviceName}`);
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a span manually (caller responsible for ending)
 */
export function createSpan(
    name: string,
    attributes?: Record<string, unknown>,
    userId?: string
): Span {
    return tracer.startSpan(name, { attributes, userId });
}

/**
 * Execute a function within a span context
 */
export async function withSpan<T>(
    name: string,
    fn: (span: Span) => Promise<T>,
    options: {
        attributes?: Record<string, unknown>;
        userId?: string;
    } = {}
): Promise<T> {
    const span = tracer.startSpan(name, options);

    try {
        const result = await fn(span);
        span.setStatus('OK');
        return result;
    } catch (error) {
        span.setStatus('ERROR', error instanceof Error ? error.message : String(error));
        if (error instanceof Error) {
            span.recordException(error);
        }
        throw error;
    } finally {
        tracer.endSpan(span);
    }
}

/**
 * Synchronous version of withSpan
 */
export function withSpanSync<T>(
    name: string,
    fn: (span: Span) => T,
    options: {
        attributes?: Record<string, unknown>;
        userId?: string;
    } = {}
): T {
    const span = tracer.startSpan(name, options);

    try {
        const result = fn(span);
        span.setStatus('OK');
        return result;
    } catch (error) {
        span.setStatus('ERROR', error instanceof Error ? error.message : String(error));
        if (error instanceof Error) {
            span.recordException(error);
        }
        throw error;
    } finally {
        tracer.endSpan(span);
    }
}

// ============================================================================
// Express Middleware
// ============================================================================

/**
 * Express middleware for automatic request tracing
 */
export function traceMiddleware() {
    return (req: any, res: any, next: any) => {
        const span = tracer.startSpan(`http.${req.method.toLowerCase()}`, {
            kind: 'SERVER',
            attributes: {
                'http.method': req.method,
                'http.url': req.url,
                'http.route': req.route?.path || req.path,
                'http.user_agent': req.headers['user-agent'] || 'unknown',
            },
        });

        // Attach span to request for nested tracing
        req.span = span;

        // Capture response
        res.on('finish', () => {
            span.setAttribute('http.status_code', res.statusCode);

            if (res.statusCode >= 400) {
                span.setStatus('ERROR', `HTTP ${res.statusCode}`);
            } else {
                span.setStatus('OK');
            }

            tracer.endSpan(span);
        });

        next();
    };
}

// ============================================================================
// Database Export (PostgreSQL)
// ============================================================================

/**
 * Export spans to PostgreSQL database
 * Call this periodically or on-demand
 */
export async function exportSpansToDb(dbPool: any): Promise<number> {
    const spans = tracer.flushSpans();
    if (spans.length === 0) return 0;

    const client = await dbPool.connect();
    try {
        for (const span of spans) {
            const data = span.toJSON();
            await client.query(
                `INSERT INTO traces 
                (trace_id, span_id, parent_span_id, name, kind, start_time, end_time, 
                 duration_ns, status_code, status_message, attributes, events, resource, user_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)`,
                [
                    data.traceId,
                    data.spanId,
                    data.parentSpanId || null,
                    data.name,
                    data.kind,
                    data.startTime,
                    data.endTime || null,
                    data.durationNs || null,
                    data.statusCode,
                    data.statusMessage || null,
                    JSON.stringify(data.attributes),
                    JSON.stringify(data.events),
                    JSON.stringify(data.resource),
                    data.userId || null,
                ]
            );
        }
        return spans.length;
    } finally {
        client.release();
    }
}
