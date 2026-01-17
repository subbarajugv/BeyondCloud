import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { config } from './config';
import providersRouter from './routes/providers';
import authRouter from './routes/auth';
import conversationsRouter from './routes/conversations';
import settingsRouter from './routes/settings';
import chatRouter from './routes/chat';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { testConnection, initializeDatabase } from './db';
import { traceMiddleware } from './tracing';

const app = express();

// =============================================================================
// Middleware
// =============================================================================

// Request tracing (OTel-compatible)
app.use(traceMiddleware());

// Security headers
app.use(helmet());

// CORS - allow frontend origin
app.use(cors({
    origin: config.frontendUrl,
    credentials: true,
}));

// Compression
app.use(compression());

// JSON body parser with increased limit for image attachments
app.use(express.json({ limit: '50mb' }));

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

// Auth routes (Phase 1)
app.use('/api/auth', authRouter);

// Conversations routes (Phase 1)
app.use('/api/conversations', conversationsRouter);

// Settings routes (Phase 3)
app.use('/api/settings', settingsRouter);

// Chat completion proxy (Phase 1)
app.use('/api/chat', chatRouter);

// =============================================================================
// Error Handling
// =============================================================================

app.use(notFoundHandler);
app.use(errorHandler);

// =============================================================================
// Start Server
// =============================================================================

const PORT = config.port;

async function startServer() {
    // Test database connection
    const dbConnected = await testConnection();

    if (!dbConnected) {
        console.error('❌ Failed to connect to database. Check DATABASE_URL in .env');
        console.log('💡 Hint: Make sure PostgreSQL is running and database exists');
        console.log('   Run: psql -c "CREATE DATABASE beyondcloud;"');
        process.exit(1);
    }

    // Initialize database schema
    try {
        await initializeDatabase();
    } catch (error) {
        console.error('❌ Failed to initialize database schema:', error);
        process.exit(1);
    }

    app.listen(PORT, () => {
        console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🌐 BeyondCloud - Backend                                ║
║                                                           ║
║   Server running on http://localhost:${PORT}               ║
║   Environment: ${config.nodeEnv.padEnd(11)}                           ║
║   Database: Connected                                     ║
║                                                           ║
║   Phase 0 - Providers:                                    ║
║   - GET  /api/health                                      ║
║   - GET  /api/providers                                   ║
║   - POST /api/providers/test                              ║
║   - GET  /api/models                                      ║
║                                                           ║
║   Phase 1 - Auth:                                         ║
║   - POST /api/auth/register                               ║
║   - POST /api/auth/login                                  ║
║   - POST /api/auth/logout                                 ║
║   - POST /api/auth/refresh                                ║
║   - POST /api/auth/forgot-password                        ║
║   - POST /api/auth/reset-password                         ║
║   - GET  /api/auth/me                                     ║
║   - PUT  /api/auth/profile                                ║
║                                                           ║
║   Phase 1 - Chat:                                         ║
║   - POST /api/chat/completions (streaming proxy)          ║
║                                                           ║
║   Phase 1 - Conversations:                                ║
║   - GET    /api/conversations                             ║
║   - POST   /api/conversations                             ║
║   - GET    /api/conversations/:id                         ║
║   - PUT    /api/conversations/:id                         ║
║   - DELETE /api/conversations/:id                         ║
║   - POST   /api/conversations/:id/messages                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
    });
}

startServer().catch(console.error);

export default app;
