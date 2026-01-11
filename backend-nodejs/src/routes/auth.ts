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

export default router;
