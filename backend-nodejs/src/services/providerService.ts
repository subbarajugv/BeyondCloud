import { config } from '../config';
import {
    Provider,
    ProviderConfig,
    ProviderTestResult,
    DEFAULT_PROVIDERS,
} from '../types/provider';

/**
 * Provider Service - Manages LLM provider configuration and testing
 */
export class ProviderService {
    private providerConfigs: Map<string, ProviderConfig> = new Map();

    constructor() {
        // Initialize with config from environment
        this.initializeProviders();
    }

    private initializeProviders(): void {
        for (const [id, providerEnv] of Object.entries(config.providers)) {
            this.providerConfigs.set(id, {
                id,
                baseUrl: providerEnv.baseUrl,
                apiKey: 'apiKey' in providerEnv ? providerEnv.apiKey : undefined,
            });
        }
    }

    /**
     * List all available providers with their current status
     */
    async listProviders(): Promise<Provider[]> {
        const providers: Provider[] = [];

        for (const [id, defaults] of Object.entries(DEFAULT_PROVIDERS)) {
            const runtimeConfig = this.providerConfigs.get(id);

            providers.push({
                ...defaults,
                baseUrl: runtimeConfig?.baseUrl || defaults.baseUrl,
                hasApiKey: defaults.hasApiKey ? !!runtimeConfig?.apiKey : false,
                isDefault: id === config.defaultLlmProvider,
                models: [], // Will be populated when fetched
            });
        }

        return providers;
    }

    /**
     * Get a specific provider configuration
     */
    getProvider(id: string): ProviderConfig | undefined {
        return this.providerConfigs.get(id);
    }

    /**
     * Test connection to a provider and fetch available models
     */
    async testProvider(id: string, apiKey?: string): Promise<ProviderTestResult> {
        const defaults = DEFAULT_PROVIDERS[id];
        if (!defaults) {
            return { success: false, error: `Unknown provider: ${id}` };
        }

        const runtimeConfig = this.providerConfigs.get(id);
        const baseUrl = runtimeConfig?.baseUrl || defaults.baseUrl;
        const key = apiKey || runtimeConfig?.apiKey;

        // Check if API key is required but not provided
        if (defaults.hasApiKey && !key) {
            return { success: false, error: 'API key required for this provider' };
        }

        try {
            const models = await this.fetchModels(baseUrl, key);
            return { success: true, models };
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Connection failed';
            return { success: false, error: message };
        }
    }

    /**
     * Fetch models from a provider
     */
    async fetchModels(baseUrl: string, apiKey?: string): Promise<string[]> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000); // 10s timeout

        try {
            const response = await fetch(`${baseUrl}/models`, {
                headers,
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Handle different response formats
            if (Array.isArray(data)) {
                return data.map((m: any) => m.id || m.name || m);
            } else if (data.data && Array.isArray(data.data)) {
                return data.data.map((m: any) => m.id || m.name || m);
            } else if (data.models && Array.isArray(data.models)) {
                return data.models.map((m: any) => m.id || m.name || m);
            }

            return ['default'];
        } finally {
            clearTimeout(timeout);
        }
    }

    /**
     * Get models for a specific provider
     */
    async getModels(providerId: string): Promise<string[]> {
        const result = await this.testProvider(providerId);
        if (result.success && result.models) {
            return result.models;
        }
        return [];
    }

    /**
     * Update provider configuration (e.g., save API key)
     */
    updateProvider(id: string, updates: Partial<ProviderConfig>): void {
        const existing = this.providerConfigs.get(id) || { id, baseUrl: '' };
        this.providerConfigs.set(id, { ...existing, ...updates });
    }
}

// Singleton instance
export const providerService = new ProviderService();
