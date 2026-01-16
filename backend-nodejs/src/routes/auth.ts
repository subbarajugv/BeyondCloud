import { Router, Request, Response } from 'express';
import bcrypt from 'bcrypt';
import { query } from '../db';
import { authenticateToken, generateToken, AuthenticatedRequest } from '../middleware/auth';

const router = Router();

const SALT_ROUNDS = 12;

interface RegisterBody {
    email: string;
    password: string;
    displayName?: string;
}

interface LoginBody {
    email: string;
    password: string;
}

/**
 * POST /api/auth/register
 * Create a new user account
 */
router.post('/register', async (req: Request<{}, {}, RegisterBody>, res: Response) => {
    const { email, password, displayName } = req.body;

    // Validation
    if (!email || !password) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Email and password are required',
            },
        });
    }

    if (password.length < 8) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Password must be at least 8 characters',
            },
        });
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Invalid email format',
            },
        });
    }

    try {
        // Check if user already exists
        const existingUsers = await query(
            'SELECT id FROM users WHERE email = $1',
            [email.toLowerCase()]
        );

        if (existingUsers.length > 0) {
            return res.status(409).json({
                error: {
                    code: 'USER_EXISTS',
                    message: 'User with this email already exists',
                },
            });
        }

        // Hash password
        const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

        // Create user
        const newUsers = await query<{ id: string; email: string; display_name: string | null }>(
            `INSERT INTO users (email, password_hash, display_name)
             VALUES ($1, $2, $3)
             RETURNING id, email, display_name`,
            [email.toLowerCase(), passwordHash, displayName || null]
        );

        const user = newUsers[0];
        const token = generateToken(user.id, user.email);

        res.status(201).json({
            user: {
                id: user.id,
                email: user.email,
                displayName: user.display_name,
            },
            token,
        });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to create account',
            },
        });
    }
});

/**
 * POST /api/auth/login
 * Login with email and password
 */
router.post('/login', async (req: Request<{}, {}, LoginBody>, res: Response) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Email and password are required',
            },
        });
    }

    try {
        // Find user
        const users = await query<{
            id: string;
            email: string;
            password_hash: string;
            display_name: string | null;
        }>(
            'SELECT id, email, password_hash, display_name FROM users WHERE email = $1',
            [email.toLowerCase()]
        );

        if (users.length === 0) {
            return res.status(401).json({
                error: {
                    code: 'INVALID_CREDENTIALS',
                    message: 'Invalid email or password',
                },
            });
        }

        const user = users[0];

        // Check password
        const passwordValid = await bcrypt.compare(password, user.password_hash);

        if (!passwordValid) {
            return res.status(401).json({
                error: {
                    code: 'INVALID_CREDENTIALS',
                    message: 'Invalid email or password',
                },
            });
        }

        // Generate token
        const token = generateToken(user.id, user.email);

        res.json({
            user: {
                id: user.id,
                email: user.email,
                displayName: user.display_name,
            },
            token,
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Login failed',
            },
        });
    }
});

/**
 * GET /api/auth/me
 * Get current user profile
 */
router.get('/me', authenticateToken, async (req: AuthenticatedRequest, res: Response) => {
    res.json({
        user: req.user,
    });
});

/**
 * POST /api/auth/logout
 * Logout (client-side token removal, this is just for logging)
 */
router.post('/logout', authenticateToken, async (req: AuthenticatedRequest, res: Response) => {
    // In a more advanced setup, we would invalidate the token server-side
    // For now, the client just removes the token
    res.json({
        success: true,
        message: 'Logged out successfully',
    });
});

/**
 * PUT /api/auth/profile
 * Update user profile
 */
router.put('/profile', authenticateToken, async (req: AuthenticatedRequest, res: Response) => {
    const { displayName } = req.body;

    if (!req.user) {
        return res.status(401).json({
            error: {
                code: 'UNAUTHORIZED',
                message: 'Not authenticated',
            },
        });
    }

    try {
        const users = await query<{ id: string; email: string; display_name: string | null }>(
            `UPDATE users SET display_name = $1 WHERE id = $2
             RETURNING id, email, display_name`,
            [displayName || null, req.user.id]
        );

        res.json({
            user: {
                id: users[0].id,
                email: users[0].email,
                displayName: users[0].display_name,
            },
        });
    } catch (error) {
        console.error('Profile update error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to update profile',
            },
        });
    }
});

/**
 * POST /api/auth/refresh
 * Refresh access token using refresh token
 */
router.post('/refresh', async (req: Request<{}, {}, { refreshToken: string }>, res: Response) => {
    const { refreshToken } = req.body;

    if (!refreshToken) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Refresh token is required',
            },
        });
    }

    try {
        const { hashToken, generateToken, generateRefreshToken } = await import('../middleware/auth');
        const tokenHash = hashToken(refreshToken);

        // Find the refresh token
        const tokens = await query<{
            id: string;
            user_id: string;
            expires_at: Date;
            revoked_at: Date | null;
        }>(
            `SELECT id, user_id, expires_at, revoked_at FROM refresh_tokens 
             WHERE token_hash = $1`,
            [tokenHash]
        );

        if (tokens.length === 0) {
            return res.status(401).json({
                error: {
                    code: 'INVALID_TOKEN',
                    message: 'Invalid refresh token',
                },
            });
        }

        const token = tokens[0];

        // Check if token is revoked
        if (token.revoked_at) {
            return res.status(401).json({
                error: {
                    code: 'TOKEN_REVOKED',
                    message: 'Refresh token has been revoked',
                },
            });
        }

        // Check if token is expired
        if (new Date(token.expires_at) < new Date()) {
            return res.status(401).json({
                error: {
                    code: 'TOKEN_EXPIRED',
                    message: 'Refresh token has expired',
                },
            });
        }

        // Get user
        const users = await query<{ id: string; email: string; display_name: string | null }>(
            'SELECT id, email, display_name FROM users WHERE id = $1',
            [token.user_id]
        );

        if (users.length === 0) {
            return res.status(401).json({
                error: {
                    code: 'USER_NOT_FOUND',
                    message: 'User not found',
                },
            });
        }

        const user = users[0];

        // Rotate refresh token (invalidate old, create new)
        await query('UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = $1', [token.id]);

        const newRefreshToken = generateRefreshToken();
        const newTokenHash = hashToken(newRefreshToken);
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 7); // 7 days

        await query(
            `INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
             VALUES ($1, $2, $3)`,
            [user.id, newTokenHash, expiresAt]
        );

        // Generate new access token
        const accessToken = generateToken(user.id, user.email);

        res.json({
            user: {
                id: user.id,
                email: user.email,
                displayName: user.display_name,
            },
            token: accessToken,
            refreshToken: newRefreshToken,
        });
    } catch (error) {
        console.error('Token refresh error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to refresh token',
            },
        });
    }
});

/**
 * POST /api/auth/forgot-password
 * Request password reset email
 */
router.post('/forgot-password', async (req: Request<{}, {}, { email: string }>, res: Response) => {
    const { email } = req.body;

    if (!email) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Email is required',
            },
        });
    }

    try {
        // Always return success to prevent email enumeration attacks
        const successResponse = {
            success: true,
            message: 'If an account exists with this email, a password reset link has been sent.',
        };

        // Find user
        const users = await query<{ id: string; email: string }>(
            'SELECT id, email FROM users WHERE email = $1',
            [email.toLowerCase()]
        );

        if (users.length === 0) {
            // Don't reveal that user doesn't exist
            return res.json(successResponse);
        }

        const user = users[0];

        // Invalidate any existing reset tokens for this user
        await query(
            'UPDATE password_reset_tokens SET used_at = NOW() WHERE user_id = $1 AND used_at IS NULL',
            [user.id]
        );

        // Generate reset token
        const { generatePasswordResetToken, hashToken } = await import('../middleware/auth');
        const resetToken = generatePasswordResetToken();
        const tokenHash = hashToken(resetToken);

        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + 1); // 1 hour expiry

        await query(
            `INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
             VALUES ($1, $2, $3)`,
            [user.id, tokenHash, expiresAt]
        );

        // In production, send email here with reset link
        // For now, log the token (development only)
        console.log(`[DEV] Password reset token for ${email}: ${resetToken}`);

        res.json(successResponse);
    } catch (error) {
        console.error('Forgot password error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to process password reset request',
            },
        });
    }
});

/**
 * POST /api/auth/reset-password
 * Reset password using token
 */
router.post('/reset-password', async (req: Request<{}, {}, { token: string; password: string }>, res: Response) => {
    const { token, password } = req.body;

    if (!token || !password) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Token and password are required',
            },
        });
    }

    if (password.length < 8) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Password must be at least 8 characters',
            },
        });
    }

    try {
        const { hashToken } = await import('../middleware/auth');
        const tokenHash = hashToken(token);

        // Find the reset token
        const tokens = await query<{
            id: string;
            user_id: string;
            expires_at: Date;
            used_at: Date | null;
        }>(
            `SELECT id, user_id, expires_at, used_at FROM password_reset_tokens 
             WHERE token_hash = $1`,
            [tokenHash]
        );

        if (tokens.length === 0) {
            return res.status(400).json({
                error: {
                    code: 'INVALID_TOKEN',
                    message: 'Invalid or expired reset token',
                },
            });
        }

        const resetToken = tokens[0];

        // Check if token is already used
        if (resetToken.used_at) {
            return res.status(400).json({
                error: {
                    code: 'TOKEN_USED',
                    message: 'This reset token has already been used',
                },
            });
        }

        // Check if token is expired
        if (new Date(resetToken.expires_at) < new Date()) {
            return res.status(400).json({
                error: {
                    code: 'TOKEN_EXPIRED',
                    message: 'Reset token has expired',
                },
            });
        }

        // Hash new password
        const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

        // Update password
        await query(
            'UPDATE users SET password_hash = $1 WHERE id = $2',
            [passwordHash, resetToken.user_id]
        );

        // Mark token as used
        await query(
            'UPDATE password_reset_tokens SET used_at = NOW() WHERE id = $1',
            [resetToken.id]
        );

        // Revoke all refresh tokens for this user (security measure)
        await query(
            'UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL',
            [resetToken.user_id]
        );

        res.json({
            success: true,
            message: 'Password has been reset successfully. Please login with your new password.',
        });
    } catch (error) {
        console.error('Reset password error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to reset password',
            },
        });
    }
});

export default router;

