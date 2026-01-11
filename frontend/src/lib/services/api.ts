/**
 * API Client for backend communication
 * Handles all /api/* endpoints for the authenticated WebUI backend
 */

import type {
    Provider,
    ProvidersResponse,
    TestProviderRequest,
    TestProviderResponse,
    ModelsResponse
} from '$lib/types/providers';

// Backend API base URL - in development, proxied through Vite
const API_BASE = '/api';

interface ApiError {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

interface ApiErrorResponse {
    error: ApiError;
}

class ApiClientError extends Error {
    code: string;
    details?: Record<string, unknown>;

    constructor(error: ApiError) {
        super(error.message);
        this.code = error.code;
        this.details = error.details;
        this.name = 'ApiClientError';
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        try {
            const errorData = (await response.json()) as ApiErrorResponse;
            throw new ApiClientError(errorData.error);
        } catch (e) {
            if (e instanceof ApiClientError) throw e;
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    }
    return response.json() as Promise<T>;
}

/**
 * Provider API endpoints
 */
export const providersApi = {
    /**
     * GET /api/providers - List all available providers
     */
    async list(): Promise<Provider[]> {
        const response = await fetch(`${API_BASE}/providers`);
        const data = await handleResponse<ProvidersResponse>(response);
        return data.providers;
    },

    /**
     * POST /api/providers/test - Test provider connection
     */
    async test(request: TestProviderRequest): Promise<TestProviderResponse> {
        const response = await fetch(`${API_BASE}/providers/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        return handleResponse<TestProviderResponse>(response);
    },

    /**
     * GET /api/models - Get models for a provider
     */
    async getModels(providerId?: string): Promise<ModelsResponse> {
        const url = providerId
            ? `${API_BASE}/models?provider=${encodeURIComponent(providerId)}`
            : `${API_BASE}/models`;
        const response = await fetch(url);
        return handleResponse<ModelsResponse>(response);
    }
};

/**
 * Health check
 */
export async function checkHealth(): Promise<{ status: string; version: string }> {
    const response = await fetch(`${API_BASE}/health`);
    return handleResponse<{ status: string; version: string }>(response);
}

export { ApiClientError };
