import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { config } from './config';
import providersRouter from './routes/providers';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';

const app = express();

// =============================================================================
// Middleware
// =============================================================================

// Security headers
app.use(helmet());

// CORS - allow frontend origin
app.use(cors({
    origin: config.frontendUrl,
    credentials: true,
}));

// Compression
app.use(compression());

// JSON body parser
app.use(express.json());

// =============================================================================
// Routes
// =============================================================================

// Health check
app.get('/api/health', (_req: Request, res: Response) => {
    res.json({
        status: 'ok',
        version: '1.0',
        timestamp: new Date().toISOString(),
    });
});

// Provider routes (Phase 0)
app.use('/api/providers', providersRouter);

// Models endpoint (convenience alias)
app.get('/api/models', (req: Request, res: Response) => {
    // Forward to providers router
    req.url = '/models';
    providersRouter(req, res, () => { });
});

// =============================================================================
// Placeholder routes for future phases
// =============================================================================

// Auth routes (Phase 1)
app.use('/api/auth', (_req, res) => {
    res.status(501).json({
        error: {
            code: 'NOT_IMPLEMENTED',
            message: 'Authentication endpoints coming in Phase 1',
        },
    });
});

// Chat completion (Phase 1)
app.post('/api/chat/completions', (_req, res) => {
    res.status(501).json({
        error: {
            code: 'NOT_IMPLEMENTED',
            message: 'Chat completion endpoint coming in Phase 1',
        },
    });
});

// =============================================================================
// Error Handling
// =============================================================================

app.use(notFoundHandler);
app.use(errorHandler);

// =============================================================================
// Start Server
// =============================================================================

const PORT = config.port;

app.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦙 llama.cpp Auth WebUI - Backend                       ║
║                                                           ║
║   Server running on http://localhost:${PORT}               ║
║   Environment: ${config.nodeEnv.padEnd(11)}                           ║
║   Default LLM: ${config.defaultLlmProvider.padEnd(11)}                           ║
║                                                           ║
║   Endpoints:                                              ║
║   - GET  /api/health                                      ║
║   - GET  /api/providers                                   ║
║   - POST /api/providers/test                              ║
║   - GET  /api/models                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
  `);
});

export default app;
