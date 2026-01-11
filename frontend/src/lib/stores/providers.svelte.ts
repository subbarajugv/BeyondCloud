/**
 * ProvidersStore - Multi-backend LLM provider management
 *
 * This store manages LLM provider selection and configuration. It provides
 * reactive state for provider switching, API key management, and connection testing.
 *
 * **Key Features:**
 * - Provider list fetching from backend
 * - Active provider selection with persistence
 * - API key management per provider
 * - Connection testing
 */

import { browser } from '$app/environment';
import { providersApi } from '$lib/services/api';
import type { Provider, ProviderTestResult } from '$lib/types/providers';

const ACTIVE_PROVIDER_KEY = 'activeProvider';
const PROVIDER_API_KEYS_KEY = 'providerApiKeys';

class ProvidersStore {
    private _providers = $state<Provider[]>([]);
    private _activeProviderId = $state<string>('ollama');
    private _loading = $state(false);
    private _testing = $state(false);
    private _error = $state<string | null>(null);
    private _apiKeys = $state<Record<string, string>>({});
    private _lastTestResult = $state<ProviderTestResult | null>(null);

    constructor() {
        if (browser) {
            this.loadFromStorage();
        }
    }

    // Getters
    get providers(): Provider[] {
        return this._providers;
    }

    get activeProviderId(): string {
        return this._activeProviderId;
    }

    get activeProvider(): Provider | null {
        return this._providers.find((p) => p.id === this._activeProviderId) ?? null;
    }

    get loading(): boolean {
        return this._loading;
    }

    get testing(): boolean {
        return this._testing;
    }

    get error(): string | null {
        return this._error;
    }

    get lastTestResult(): ProviderTestResult | null {
        return this._lastTestResult;
    }

    /**
     * Get API key for a provider (masked for display)
     */
    getApiKeyMasked(providerId: string): string {
        const key = this._apiKeys[providerId];
        if (!key) return '';
        if (key.length <= 8) return '***';
        return key.slice(0, 4) + '***' + key.slice(-4);
    }

    /**
     * Check if a provider has an API key set
     */
    hasApiKey(providerId: string): boolean {
        return !!this._apiKeys[providerId];
    }

    /**
     * Load state from localStorage
     */
    private loadFromStorage(): void {
        try {
            const savedProvider = localStorage.getItem(ACTIVE_PROVIDER_KEY);
            if (savedProvider) {
                this._activeProviderId = savedProvider;
            }

            const savedKeys = localStorage.getItem(PROVIDER_API_KEYS_KEY);
            if (savedKeys) {
                this._apiKeys = JSON.parse(savedKeys);
            }
        } catch (error) {
            console.warn('Failed to load provider settings from localStorage:', error);
        }
    }

    /**
     * Save state to localStorage
     */
    private saveToStorage(): void {
        if (!browser) return;

        try {
            localStorage.setItem(ACTIVE_PROVIDER_KEY, this._activeProviderId);
            localStorage.setItem(PROVIDER_API_KEYS_KEY, JSON.stringify(this._apiKeys));
        } catch (error) {
            console.error('Failed to save provider settings:', error);
        }
    }

    /**
     * Fetch available providers from backend
     */
    async fetchProviders(): Promise<void> {
        if (this._loading) return;

        this._loading = true;
        this._error = null;

        try {
            const providers = await providersApi.list();
            this._providers = providers;

            // Update hasApiKey based on stored keys
            this._providers = providers.map((p) => ({
                ...p,
                hasApiKey: p.hasApiKey ? this.hasApiKey(p.id) : false
            }));

            // If active provider doesn't exist in list, switch to default
            const activeExists = providers.some((p) => p.id === this._activeProviderId);
            if (!activeExists) {
                const defaultProvider = providers.find((p) => p.isDefault) || providers[0];
                if (defaultProvider) {
                    this._activeProviderId = defaultProvider.id;
                    this.saveToStorage();
                }
            }
        } catch (error) {
            this._error = error instanceof Error ? error.message : 'Failed to fetch providers';
            console.error('Error fetching providers:', error);
        } finally {
            this._loading = false;
        }
    }

    /**
     * Select a provider as active
     */
    selectProvider(providerId: string): void {
        if (this._activeProviderId === providerId) return;

        const provider = this._providers.find((p) => p.id === providerId);
        if (!provider) {
            console.warn(`Provider ${providerId} not found`);
            return;
        }

        this._activeProviderId = providerId;
        this._lastTestResult = null;
        this.saveToStorage();
    }

    /**
     * Set API key for a provider
     */
    setApiKey(providerId: string, apiKey: string): void {
        if (apiKey) {
            this._apiKeys[providerId] = apiKey;
        } else {
            delete this._apiKeys[providerId];
        }

        // Update provider's hasApiKey status
        this._providers = this._providers.map((p) =>
            p.id === providerId ? { ...p, hasApiKey: !!apiKey } : p
        );

        this.saveToStorage();
    }

    /**
     * Test connection to a provider
     */
    async testProvider(providerId?: string): Promise<ProviderTestResult> {
        const id = providerId || this._activeProviderId;
        const apiKey = this._apiKeys[id];

        this._testing = true;
        this._lastTestResult = null;

        try {
            const result = await providersApi.test({ id, apiKey });
            this._lastTestResult = {
                success: result.success,
                models: result.models
            };

            // Update provider's models list
            if (result.success && result.models) {
                this._providers = this._providers.map((p) =>
                    p.id === id ? { ...p, models: result.models || [] } : p
                );
            }

            return this._lastTestResult;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Connection test failed';
            this._lastTestResult = {
                success: false,
                error: errorMessage
            };
            return this._lastTestResult;
        } finally {
            this._testing = false;
        }
    }

    /**
     * Get the API key for a provider (for internal use in requests)
     */
    getApiKey(providerId: string): string | undefined {
        return this._apiKeys[providerId];
    }

    /**
     * Clear all stored data
     */
    clear(): void {
        this._providers = [];
        this._activeProviderId = 'llama.cpp';
        this._apiKeys = {};
        this._lastTestResult = null;
        this._error = null;

        if (browser) {
            localStorage.removeItem(ACTIVE_PROVIDER_KEY);
            localStorage.removeItem(PROVIDER_API_KEYS_KEY);
        }
    }
}

// Create and export the store instance
export const providersStore = new ProvidersStore();

// Export reactive getters
export const providers = () => providersStore.providers;
export const activeProviderId = () => providersStore.activeProviderId;
export const activeProvider = () => providersStore.activeProvider;
export const providersLoading = () => providersStore.loading;
export const providersTesting = () => providersStore.testing;
export const providersError = () => providersStore.error;
export const lastTestResult = () => providersStore.lastTestResult;

// Export bound methods
export const fetchProviders = providersStore.fetchProviders.bind(providersStore);
export const selectProvider = providersStore.selectProvider.bind(providersStore);
export const setProviderApiKey = providersStore.setApiKey.bind(providersStore);
export const testProvider = providersStore.testProvider.bind(providersStore);
export const getProviderApiKey = providersStore.getApiKey.bind(providersStore);
export const hasProviderApiKey = providersStore.hasApiKey.bind(providersStore);
export const getProviderApiKeyMasked = providersStore.getApiKeyMasked.bind(providersStore);
