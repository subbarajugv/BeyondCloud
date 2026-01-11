import { Request, Response, NextFunction } from 'express';

interface AppError extends Error {
    statusCode?: number;
    code?: string;
    details?: Record<string, unknown>;
}

/**
 * Global error handler middleware
 */
export function errorHandler(
    err: AppError,
    _req: Request,
    res: Response,
    _next: NextFunction
): void {
    console.error('Error:', err);

    const statusCode = err.statusCode || 500;
    const code = err.code || 'SERVER_ERROR';
    const message = err.message || 'An unexpected error occurred';

    res.status(statusCode).json({
        error: {
            code,
            message,
            ...(err.details && { details: err.details }),
        },
    });
}

/**
 * 404 Not Found handler
 */
export function notFoundHandler(req: Request, res: Response): void {
    res.status(404).json({
        error: {
            code: 'NOT_FOUND',
            message: `Route ${req.method} ${req.path} not found`,
        },
    });
}
