import { Router, Response } from 'express';
import { query } from '../db';
import { authenticateToken, AuthenticatedRequest } from '../middleware/auth';

const router = Router();

interface UserSettings {
    user_id: string;
    settings: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

/**
 * GET /api/settings
 * Get current user's settings
 */
router.get('/', authenticateToken, async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({
            error: {
                code: 'UNAUTHORIZED',
                message: 'Not authenticated',
            },
        });
    }

    try {
        const results = await query<UserSettings>(
            'SELECT settings FROM user_settings WHERE user_id = $1',
            [req.user.id]
        );

        if (results.length === 0) {
            // Return empty settings if none exist yet
            return res.json({ settings: {} });
        }

        res.json({ settings: results[0].settings });
    } catch (error) {
        console.error('Get settings error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to get settings',
            },
        });
    }
});

/**
 * PUT /api/settings
 * Update current user's settings (merge with existing)
 */
router.put('/', authenticateToken, async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({
            error: {
                code: 'UNAUTHORIZED',
                message: 'Not authenticated',
            },
        });
    }

    const { settings } = req.body;

    if (!settings || typeof settings !== 'object') {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Settings object is required',
            },
        });
    }

    try {
        // Upsert: insert or update, merging with existing settings
        const results = await query<UserSettings>(
            `INSERT INTO user_settings (user_id, settings)
             VALUES ($1, $2)
             ON CONFLICT (user_id) 
             DO UPDATE SET settings = user_settings.settings || $2
             RETURNING settings`,
            [req.user.id, JSON.stringify(settings)]
        );

        res.json({ settings: results[0].settings });
    } catch (error) {
        console.error('Update settings error:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to update settings',
            },
        });
    }
});

export default router;
