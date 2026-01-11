import { Router, Request, Response } from 'express';
import { providerService } from '../services/providerService';

const router = Router();

/**
 * GET /api/providers
 * List all available LLM providers
 */
router.get('/', async (_req: Request, res: Response) => {
    try {
        const providers = await providerService.listProviders();
        res.json({ providers });
    } catch (error) {
        console.error('Error listing providers:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to list providers',
            },
        });
    }
});

/**
 * POST /api/providers/test
 * Test connection to a provider
 * Body: { id: string, apiKey?: string, baseUrl?: string }
 */
router.post('/test', async (req: Request, res: Response) => {
    const { id, apiKey, baseUrl } = req.body;

    if (!id) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Provider id is required',
                details: { field: 'id' },
            },
        });
    }

    try {
        // If custom baseUrl provided, update temporarily
        if (baseUrl) {
            providerService.updateProvider(id, { baseUrl });
        }

        const result = await providerService.testProvider(id, apiKey);

        if (result.success) {
            res.json({
                success: true,
                models: result.models,
            });
        } else {
            res.status(502).json({
                error: {
                    code: 'LLM_ERROR',
                    message: result.error || 'Provider connection failed',
                },
            });
        }
    } catch (error) {
        console.error('Error testing provider:', error);
        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to test provider',
            },
        });
    }
});

/**
 * GET /api/models
 * Get available models for the active/specified provider
 * Query: ?provider=openai (optional)
 */
router.get('/models', async (req: Request, res: Response) => {
    const providerId = (req.query.provider as string) || 'llama.cpp';

    try {
        const models = await providerService.getModels(providerId);
        res.json({ models, provider: providerId });
    } catch (error) {
        console.error('Error fetching models:', error);
        res.status(502).json({
            error: {
                code: 'LLM_ERROR',
                message: 'Failed to fetch models from provider',
            },
        });
    }
});

export default router;
