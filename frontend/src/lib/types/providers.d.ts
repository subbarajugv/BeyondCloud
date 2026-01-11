/**
 * Provider types for multi-backend LLM integration
 */

export interface Provider {
    id: string;
    name: string;
    baseUrl: string;
    hasApiKey: boolean;
    isDefault: boolean;
    models: string[];
}

export interface ProviderConfig {
    id: string;
    apiKey?: string;
    baseUrl?: string;
}

export interface ProviderTestResult {
    success: boolean;
    models?: string[];
    error?: string;
}

export interface ProvidersResponse {
    providers: Provider[];
}

export interface TestProviderRequest {
    id: string;
    apiKey?: string;
    baseUrl?: string;
}

export interface TestProviderResponse {
    success: boolean;
    models?: string[];
}

export interface ModelsResponse {
    models: string[];
    provider: string;
}
