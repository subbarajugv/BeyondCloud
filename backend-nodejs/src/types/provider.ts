// Provider types for Multi-Backend LLM Integration

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
    baseUrl: string;
    apiKey?: string;
    defaultModel?: string;
}

export interface LLMMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

export interface LLMRequest {
    messages: LLMMessage[];
    model?: string;
    provider?: string;
    stream?: boolean;
    temperature?: number;
    max_tokens?: number;
}

export interface LLMChoice {
    message?: {
        role: string;
        content: string;
    };
    delta?: {
        content?: string;
    };
    index: number;
    finish_reason?: string;
}

export interface LLMResponse {
    choices: LLMChoice[];
    model: string;
    usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
}

export interface ProviderTestResult {
    success: boolean;
    models?: string[];
    error?: string;
}

// Default provider configurations
export const DEFAULT_PROVIDERS: Record<string, Omit<Provider, 'models'>> = {
    'llama.cpp': {
        id: 'llama.cpp',
        name: 'llama.cpp (Local)',
        baseUrl: 'http://localhost:8080/v1',
        hasApiKey: false,
        isDefault: false,
    },
    'ollama': {
        id: 'ollama',
        name: 'Ollama (Local)',
        baseUrl: 'http://localhost:11434/v1',
        hasApiKey: false,
        isDefault: true,
    },
    'openai': {
        id: 'openai',
        name: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        hasApiKey: true,
        isDefault: false,
    },
    'gemini': {
        id: 'gemini',
        name: 'Google Gemini',
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
        hasApiKey: true,
        isDefault: false,
    },
    'groq': {
        id: 'groq',
        name: 'Groq',
        baseUrl: 'https://api.groq.com/openai/v1',
        hasApiKey: true,
        isDefault: false,
    },
};
