import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { config } from '../config';
import { query } from '../db';

export interface JwtPayload {
    userId: string;
    email: string;
    iat?: number;
    exp?: number;
}

export interface AuthenticatedRequest extends Request {
    user?: {
        id: string;
        email: string;
        displayName: string | null;
        role: string;  // RBAC role: user, rag_user, agent_user, admin, owner
    };
}

/**
 * Middleware to verify JWT token and attach user to request
 */
export async function authenticateToken(
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
): Promise<void> {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

    if (!token) {
        res.status(401).json({
            error: {
                code: 'UNAUTHORIZED',
                message: 'Authentication required',
            },
        });
        return;
    }

    try {
        const payload = jwt.verify(token, config.jwtSecret) as JwtPayload;

        // Fetch user from database
        const users = await query<{ id: string; email: string; display_name: string | null; role: string }>(
            'SELECT id, email, display_name, role FROM users WHERE id = $1',
            [payload.userId]
        );

        if (users.length === 0) {
            res.status(401).json({
                error: {
                    code: 'UNAUTHORIZED',
                    message: 'User not found',
                },
            });
            return;
        }

        req.user = {
            id: users[0].id,
            email: users[0].email,
            displayName: users[0].display_name,
            role: users[0].role || 'user',
        };

        next();
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            res.status(401).json({
                error: {
                    code: 'TOKEN_EXPIRED',
                    message: 'Token has expired',
                },
            });
            return;
        }

        res.status(403).json({
            error: {
                code: 'FORBIDDEN',
                message: 'Invalid token',
            },
        });
    }
}

/**
 * Optional authentication - doesn't fail if no token, but attaches user if present
 */
export async function optionalAuth(
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
): Promise<void> {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return next();
    }

    try {
        const payload = jwt.verify(token, config.jwtSecret) as JwtPayload;

        const users = await query<{ id: string; email: string; display_name: string | null; role: string }>(
            'SELECT id, email, display_name, role FROM users WHERE id = $1',
            [payload.userId]
        );

        if (users.length > 0) {
            req.user = {
                id: users[0].id,
                email: users[0].email,
                displayName: users[0].display_name,
                role: users[0].role || 'user',
            };
        }
    } catch {
        // Token invalid, but that's okay for optional auth
    }

    next();
}

/**
 * Generate JWT token for a user
 */
export function generateToken(userId: string, email: string): string {
    const payload: JwtPayload = {
        userId,
        email,
    };

    return jwt.sign(payload, config.jwtSecret, {
        expiresIn: config.jwtExpiresIn,
    });
}

/**
 * Generate a short-lived access token (15 minutes)
 */
export function generateAccessToken(userId: string, email: string): string {
    const payload: JwtPayload = {
        userId,
        email,
    };

    return jwt.sign(payload, config.jwtSecret, {
        expiresIn: `${config.accessTokenExpireMinutes}m`,
    });
}

/**
 * Generate a random refresh token
 */
export function generateRefreshToken(): string {
    const crypto = require('crypto');
    return crypto.randomBytes(64).toString('hex');
}

/**
 * Hash a token for secure storage
 */
export function hashToken(token: string): string {
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(token).digest('hex');
}

/**
 * Generate a password reset token (random string)
 */
export function generatePasswordResetToken(): string {
    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
}
