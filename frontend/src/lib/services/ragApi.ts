/**
 * RAG API Client for Python AI Service
 * Handles document ingestion, retrieval, and querying
 */

// Python AI Service base URL
const RAG_API_BASE = 'http://localhost:8001/api';

// Types
export interface RAGSource {
    id: string;
    name: string;
    type: string;
    chunk_count: number;
    file_size?: number;
    metadata?: Record<string, unknown>;
    created_at: string;
}

export interface RAGChunk {
    id: string;
    source_id: string;
    content: string;
    score: number;
    metadata?: Record<string, unknown>;
}

export interface IngestRequest {
    name: string;
    content: string;
    chunk_size?: number;
    chunk_overlap?: number;
    metadata?: Record<string, unknown>;
}

export interface IngestResponse {
    source_id: string;
    name: string;
    chunk_count: number;
    message: string;
}

export interface QueryRequest {
    query: string;
    top_k?: number;
    min_score?: number;
    use_hybrid?: boolean;
    use_reranking?: boolean;
    generate?: boolean;
}

export interface Citation {
    source_id: string;
    source_name: string;
    score: number;
    content_preview?: string;
}

export interface QueryResponse {
    query: string;
    chunks: RAGChunk[];
    answer?: string;
    citations: Citation[];
    model?: string;
    error?: string;
    search_mode?: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`RAG API Error ${response.status}: ${text}`);
    }
    return response.json() as Promise<T>;
}

/**
 * RAG API endpoints
 */
export const ragApi = {
    /**
     * GET /api/rag/sources - List all documents
     */
    async listSources(): Promise<RAGSource[]> {
        const response = await fetch(`${RAG_API_BASE}/rag/sources`);
        return handleResponse<RAGSource[]>(response);
    },

    /**
     * POST /api/rag/ingest - Ingest text content
     */
    async ingestText(request: IngestRequest): Promise<IngestResponse> {
        const response = await fetch(`${RAG_API_BASE}/rag/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        return handleResponse<IngestResponse>(response);
    },

    /**
     * POST /api/rag/ingest/file - Upload and ingest file
     */
    async ingestFile(
        file: File,
        chunkSize: number = 500,
        chunkOverlap: number = 50
    ): Promise<IngestResponse> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chunk_size', chunkSize.toString());
        formData.append('chunk_overlap', chunkOverlap.toString());

        const response = await fetch(`${RAG_API_BASE}/rag/ingest/file`, {
            method: 'POST',
            body: formData
        });
        return handleResponse<IngestResponse>(response);
    },

    /**
     * POST /api/rag/query - Query documents with optional answer generation
     */
    async query(request: QueryRequest): Promise<QueryResponse> {
        const response = await fetch(`${RAG_API_BASE}/rag/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        return handleResponse<QueryResponse>(response);
    },

    /**
     * POST /api/rag/retrieve - Vector search only
     */
    async retrieve(
        query: string,
        topK: number = 5,
        minScore: number = 0.5
    ): Promise<RAGChunk[]> {
        const response = await fetch(`${RAG_API_BASE}/rag/retrieve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: topK, min_score: minScore })
        });
        return handleResponse<RAGChunk[]>(response);
    },

    /**
     * DELETE /api/rag/sources/{id} - Delete a document
     */
    async deleteSource(sourceId: string): Promise<{ deleted: boolean }> {
        const response = await fetch(`${RAG_API_BASE}/rag/sources/${sourceId}`, {
            method: 'DELETE'
        });
        return handleResponse<{ deleted: boolean }>(response);
    }
};

export default ragApi;
