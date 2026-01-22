/**
 * RAG Settings API Client
 * Handles fetching and updating user's RAG pipeline settings
 */

import { getAccessToken } from './api';

// Python AI Service base URL (same as ragApi.ts)
const RAG_API_BASE = 'http://localhost:8001/api';

/**
 * RAG Settings type matching backend schema
 */
export interface RAGSettings {
    // Embedding Configuration
    embedding_provider: 'sentence_transformers' | 'openai' | 'ollama';
    embedding_model: string;

    // Chunking
    chunk_size: number;
    chunk_overlap: number;
    use_sentence_boundary: boolean;

    // Search & Reranking
    use_hybrid_search: boolean;
    bm25_weight: number;
    use_reranking: boolean;
    reranker_model: string;
    rerank_top_k: number;
    min_score: number;

    // Context Assembly
    context_max_tokens: number;
    context_ordering: 'score_desc' | 'score_asc' | 'position';

    // Grounding
    require_citations: boolean;
    max_citations: number;
    rag_system_prompt: string | null;
}

/**
 * Available embedding providers and their models
 */
export interface EmbeddingModel {
    name: string;
    dimensions: number;
}

export interface EmbeddingProvider {
    name: string;
    models: EmbeddingModel[];
}

export interface EmbeddingModelsResponse {
    providers: EmbeddingProvider[];
}

/**
 * Default RAG settings (matches backend defaults)
 */
export const DEFAULT_RAG_SETTINGS: RAGSettings = {
    embedding_provider: 'sentence_transformers',
    embedding_model: 'all-MiniLM-L6-v2',
    chunk_size: 500,
    chunk_overlap: 50,
    use_sentence_boundary: true,
    use_hybrid_search: true,
    bm25_weight: 0.3,
    use_reranking: true,
    reranker_model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
    rerank_top_k: 5,
    min_score: 0.3,
    context_max_tokens: 4000,
    context_ordering: 'score_desc',
    require_citations: true,
    max_citations: 5,
    rag_system_prompt: null,
};

/**
 * Get auth headers for API requests
 */
function getAuthHeaders(): HeadersInit {
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    const token = getAccessToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

/**
 * Fetch user's RAG settings from backend
 */
export async function getRAGSettings(): Promise<RAGSettings> {
    const response = await fetch(`${RAG_API_BASE}/rag/settings`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        console.warn('Failed to fetch RAG settings, using defaults');
        return { ...DEFAULT_RAG_SETTINGS };
    }

    const data = await response.json();
    return { ...DEFAULT_RAG_SETTINGS, ...data };
}

/**
 * Update user's RAG settings (partial update)
 */
export async function updateRAGSettings(
    settings: Partial<RAGSettings>
): Promise<RAGSettings> {
    const response = await fetch(`${RAG_API_BASE}/rag/settings`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(settings),
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to update RAG settings: ${error}`);
    }

    return response.json();
}

/**
 * Reset settings to defaults
 */
export async function resetRAGSettings(): Promise<RAGSettings> {
    return updateRAGSettings(DEFAULT_RAG_SETTINGS);
}

/**
 * Fetch available embedding models from backend
 */
export async function getEmbeddingModels(): Promise<EmbeddingModelsResponse> {
    const response = await fetch(`${RAG_API_BASE}/rag/embedding-models`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        console.warn('Failed to fetch embedding models');
        // Return default fallback
        return {
            providers: [
                {
                    name: 'sentence_transformers',
                    models: [
                        { name: 'all-MiniLM-L6-v2', dimensions: 384 },
                        { name: 'all-mpnet-base-v2', dimensions: 768 },
                    ]
                },
                {
                    name: 'openai',
                    models: [
                        { name: 'text-embedding-3-small', dimensions: 1536 },
                        { name: 'text-embedding-3-large', dimensions: 3072 },
                    ]
                },
                {
                    name: 'ollama',
                    models: [
                        { name: 'nomic-embed-text', dimensions: 768 },
                        { name: 'mxbai-embed-large', dimensions: 1024 },
                    ]
                }
            ]
        };
    }

    return response.json();
}
