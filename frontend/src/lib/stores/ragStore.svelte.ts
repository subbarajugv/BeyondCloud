/**
 * RAG Store - State management for document ingestion and retrieval
 */
import { ragApi, type RAGSource, type RAGChunk, type QueryResponse } from '$lib/services/ragApi';
import { browser } from '$app/environment';
import { toast } from 'svelte-sonner';

class RAGStore {
    sources = $state<RAGSource[]>([]);
    isLoading = $state(false);
    isUploading = $state(false);
    selectedSourceIds = $state<string[]>([]);
    lastQueryResult = $state<QueryResponse | null>(null);
    error = $state<string | null>(null);

    constructor() {
        if (browser) {
            this.loadSources();
        }
    }

    /**
     * Load all document sources from the API
     */
    async loadSources(): Promise<void> {
        this.isLoading = true;
        this.error = null;
        try {
            this.sources = await ragApi.listSources();
        } catch (e) {
            const error = e as Error;
            this.error = error.message;
            console.error('Failed to load RAG sources:', error);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Ingest text content
     */
    async ingestText(
        name: string,
        content: string,
        chunkSize: number = 500,
        chunkOverlap: number = 50
    ): Promise<boolean> {
        this.isUploading = true;
        this.error = null;
        try {
            const result = await ragApi.ingestText({
                name,
                content,
                chunk_size: chunkSize,
                chunk_overlap: chunkOverlap
            });
            toast.success(`Ingested ${result.chunk_count} chunks from "${name}"`);
            await this.loadSources();
            return true;
        } catch (e) {
            const error = e as Error;
            this.error = error.message;
            toast.error(`Failed to ingest: ${error.message}`);
            return false;
        } finally {
            this.isUploading = false;
        }
    }

    /**
     * Ingest a file
     */
    async ingestFile(
        file: File,
        chunkSize: number = 500,
        chunkOverlap: number = 50
    ): Promise<boolean> {
        this.isUploading = true;
        this.error = null;
        try {
            const result = await ragApi.ingestFile(file, chunkSize, chunkOverlap);
            toast.success(`Ingested ${result.chunk_count} chunks from "${file.name}"`);
            await this.loadSources();
            return true;
        } catch (e) {
            const error = e as Error;
            this.error = error.message;
            toast.error(`Failed to ingest file: ${error.message}`);
            return false;
        } finally {
            this.isUploading = false;
        }
    }

    /**
     * Delete a document source
     */
    async deleteSource(sourceId: string): Promise<boolean> {
        try {
            await ragApi.deleteSource(sourceId);
            this.sources = this.sources.filter(s => s.id !== sourceId);
            this.selectedSourceIds = this.selectedSourceIds.filter(id => id !== sourceId);
            toast.success('Document deleted');
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to delete: ${error.message}`);
            return false;
        }
    }

    /**
     * Toggle source selection for queries
     */
    toggleSourceSelection(sourceId: string): void {
        if (this.selectedSourceIds.includes(sourceId)) {
            this.selectedSourceIds = this.selectedSourceIds.filter(id => id !== sourceId);
        } else {
            this.selectedSourceIds = [...this.selectedSourceIds, sourceId];
        }
    }

    /**
     * Select/deselect all sources
     */
    selectAllSources(select: boolean): void {
        this.selectedSourceIds = select ? this.sources.map(s => s.id) : [];
    }

    /**
     * Query documents with optional answer generation
     */
    async query(
        queryText: string,
        options: {
            topK?: number;
            minScore?: number;
            useHybrid?: boolean;
            useReranking?: boolean;
            generate?: boolean;
        } = {}
    ): Promise<QueryResponse | null> {
        this.isLoading = true;
        this.error = null;
        try {
            const result = await ragApi.query({
                query: queryText,
                top_k: options.topK ?? 5,
                min_score: options.minScore ?? 0.5,
                use_hybrid: options.useHybrid ?? false,
                use_reranking: options.useReranking ?? false,
                generate: options.generate ?? false
            });
            this.lastQueryResult = result;
            return result;
        } catch (e) {
            const error = e as Error;
            this.error = error.message;
            toast.error(`Query failed: ${error.message}`);
            return null;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Get source by ID
     */
    getSource(sourceId: string): RAGSource | undefined {
        return this.sources.find(s => s.id === sourceId);
    }
}

export const ragStore = new RAGStore();
