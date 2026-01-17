/**
 * OpenTelemetry Tracing Setup
 * 
 * This module initializes OpenTelemetry tracing for the Node.js backend.
 * It should be imported at the very top of index.ts (before other imports).
 * 
 * Configuration via environment variables:
 * - OTEL_SERVICE_NAME: Service name (default: beyondcloud-nodejs)
 * - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (optional)
 * - OTEL_TRACES_EXPORTER: console, otlp, or none (default: console)
 */

import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { ConsoleSpanExporter, SimpleSpanProcessor, BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { diag, DiagConsoleLogger, DiagLogLevel, trace, context, SpanStatusCode } from '@opentelemetry/api';

// Enable debug logging in development
if (process.env.OTEL_DEBUG === 'true') {
    diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
}

const serviceName = process.env.OTEL_SERVICE_NAME || 'beyondcloud-nodejs';
const serviceVersion = process.env.npm_package_version || '1.0.0';

// Configure exporter based on environment
function getExporter() {
    const exporterType = process.env.OTEL_TRACES_EXPORTER || 'console';

    if (exporterType === 'otlp') {
        const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces';
        console.log(`[OTel] Using OTLP exporter: ${endpoint}`);
        return new OTLPTraceExporter({ url: endpoint });
    }

    if (exporterType === 'none') {
        console.log('[OTel] Tracing disabled');
        return undefined;
    }

    console.log('[OTel] Using console exporter');
    return new ConsoleSpanExporter();
}

// Initialize the SDK
const exporter = getExporter();

const sdk = new NodeSDK({
    resource: new Resource({
        [ATTR_SERVICE_NAME]: serviceName,
        [ATTR_SERVICE_VERSION]: serviceVersion,
    }),
    spanProcessor: exporter
        ? new BatchSpanProcessor(exporter)
        : undefined,
    instrumentations: [
        getNodeAutoInstrumentations({
            // Disable some noisy instrumentations
            '@opentelemetry/instrumentation-fs': { enabled: false },
            '@opentelemetry/instrumentation-dns': { enabled: false },
        }),
    ],
});

// Start the SDK
sdk.start();
console.log(`[OTel] Tracing initialized for service: ${serviceName}`);

// Graceful shutdown
process.on('SIGTERM', () => {
    sdk.shutdown()
        .then(() => console.log('[OTel] Tracing terminated'))
        .catch((error) => console.error('[OTel] Error terminating tracing', error))
        .finally(() => process.exit(0));
});

// Export helper functions for manual instrumentation
export const tracer = trace.getTracer(serviceName, serviceVersion);

/**
 * Create a span for tracing an operation
 * 
 * @example
 * const result = await withSpan('user.authenticate', async (span) => {
 *     span.setAttribute('user.id', userId);
 *     return await authenticateUser(userId);
 * });
 */
export async function withSpan<T>(
    name: string,
    fn: (span: ReturnType<typeof tracer.startSpan>) => Promise<T>,
    attributes?: Record<string, string | number | boolean>
): Promise<T> {
    const span = tracer.startSpan(name, { attributes });

    try {
        const result = await context.with(trace.setSpan(context.active(), span), () => fn(span));
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
    } catch (error) {
        span.setStatus({
            code: SpanStatusCode.ERROR,
            message: error instanceof Error ? error.message : String(error),
        });
        span.recordException(error instanceof Error ? error : new Error(String(error)));
        throw error;
    } finally {
        span.end();
    }
}

/**
 * Middleware to trace HTTP requests with custom attributes
 */
export function traceMiddleware(operationName: string) {
    return async (req: any, res: any, next: any) => {
        const span = tracer.startSpan(`http.${operationName}`, {
            attributes: {
                'http.method': req.method,
                'http.url': req.url,
                'http.user_agent': req.headers['user-agent'] || 'unknown',
            },
        });

        // Add user ID if available
        if (req.user?.id) {
            span.setAttribute('user.id', req.user.id);
        }

        // Store span in request for nested tracing
        req.span = span;

        res.on('finish', () => {
            span.setAttribute('http.status_code', res.statusCode);
            if (res.statusCode >= 400) {
                span.setStatus({ code: SpanStatusCode.ERROR });
            } else {
                span.setStatus({ code: SpanStatusCode.OK });
            }
            span.end();
        });

        next();
    };
}

export { trace, context, SpanStatusCode };
