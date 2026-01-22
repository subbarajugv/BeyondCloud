import { Router, Request, Response } from 'express';
import { config } from '../config';
import { authenticateToken, AuthenticatedRequest, optionalAuth } from '../middleware/auth';

const router = Router();

/**
 * POST /api/chat/completions
 * Proxy chat completions to the configured LLM provider
 * Supports streaming responses (SSE)
 * 
 * Can route through Python LLM Gateway when USE_PYTHON_LLM_GATEWAY=true
 */
router.post('/completions', optionalAuth, async (req: AuthenticatedRequest, res: Response) => {
    const { messages, model, stream = true, ...options } = req.body;

    if (!messages || !Array.isArray(messages)) {
        return res.status(400).json({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Messages array is required',
            },
        });
    }

    try {
        let baseUrl: string;
        let apiKey: string | undefined;

        // Check if we should route through Python LLM Gateway
        if (config.usePythonLlmGateway) {
            // Route through Python backend for unified LLM management
            baseUrl = `${config.pythonBackendUrl}/api/llm`;
            apiKey = undefined; // Python handles auth
            console.log('[LLM Gateway] Routing through Python backend');
        } else {
            // Direct routing to LLM provider (legacy behavior)
            const providerConfig = config.providers['ollama'] || config.providers['llama.cpp'];
            baseUrl = providerConfig.baseUrl;
            apiKey = 'apiKey' in providerConfig ? (providerConfig as { apiKey?: string }).apiKey : undefined;
        }

        // Build headers
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }

        // Determine endpoint path
        const endpoint = config.usePythonLlmGateway
            ? `${baseUrl}/chat`  // Python gateway endpoint
            : `${baseUrl}/chat/completions`;  // Direct LLM endpoint

        // Make request to LLM provider or gateway
        const response = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                messages,
                model,
                stream,
                ...options,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`LLM provider error: ${response.status}`, errorText);
            return res.status(response.status).json({
                error: {
                    code: 'PROVIDER_ERROR',
                    message: `LLM provider returned error: ${response.status}`,
                    details: errorText,
                },
            });
        }

        // Handle streaming response
        if (stream && response.body) {
            // Set SSE headers
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering

            // Stream the response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            try {
                while (true) {
                    const { done, value } = await reader.read();

                    if (done) {
                        res.end();
                        break;
                    }

                    const chunk = decoder.decode(value, { stream: true });
                    res.write(chunk);
                }
            } catch (streamError) {
                console.error('Streaming error:', streamError);
                res.end();
            }
        } else {
            // Non-streaming response
            const data = await response.json();
            res.json(data);
        }
    } catch (error) {
        console.error('Chat completion error:', error);

        if (error instanceof Error && error.message.includes('fetch')) {
            return res.status(503).json({
                error: {
                    code: 'PROVIDER_UNAVAILABLE',
                    message: 'LLM provider is not available. Check if the server is running.',
                },
            });
        }

        res.status(500).json({
            error: {
                code: 'SERVER_ERROR',
                message: 'Failed to process chat completion',
            },
        });
    }
});

export default router;
