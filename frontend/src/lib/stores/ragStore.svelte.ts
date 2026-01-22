/**
 * RAG Store - State management for document ingestion and retrieval
 */
import { ragApi, type RAGSource, type RAGChunk, type QueryResponse, type VisibilityType, type RAGCollection, type CollectionCreateRequest, type CollectionVisibility, type Citation } from '$lib/services/ragApi';
import { browser } from '$app/environment';
import { toast } from 'svelte-sonner';

class RAGStore {
    sources = $state<RAGSource[]>([]);
    collections = $state<RAGCollection[]>([]);
    collectionTree = $state<RAGCollection[]>([]);
    currentCollectionId = $state<string | null>(null);
    isLoading = $state(false);
    isUploading = $state(false);
    selectedSourceIds = $state<string[]>([]);
    lastQueryResult = $state<QueryResponse | null>(null);
    error = $state<string | null>(null);

    // RAG context injection toggle
    ragEnabled = $state(true);

    // Advanced RAG Settings (Local state)
    advancedMode = $state(false);
    contextBudget = $state(4096);
    hybridRatio = $state(0.7);

    // Last retrieved chunks for citation display
    lastRetrievedChunks = $state<RAGChunk[]>([]);

    // Computed: Separate private and shared sources
    get privateSources(): RAGSource[] {
        return this.sources.filter(s => s.visibility === 'private');
    }

    get sharedSources(): RAGSource[] {
        return this.sources.filter(s => s.visibility === 'shared');
    }

    get ownedSources(): RAGSource[] {
        return this.sources.filter(s => s.is_owner === true);
    }

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
        chunkOverlap: number = 50,
        visibility: VisibilityType = 'private'
    ): Promise<boolean> {
        this.isUploading = true;
        this.error = null;
        try {
            const result = await ragApi.ingestText({
                name,
                content,
                chunk_size: chunkSize,
                chunk_overlap: chunkOverlap,
                visibility
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
        chunkOverlap: number = 50,
        visibility: VisibilityType = 'private'
    ): Promise<boolean> {
        this.isUploading = true;
        this.error = null;
        try {
            const result = await ragApi.ingestFile(file, chunkSize, chunkOverlap, visibility);
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
     * Update source visibility (admin only)
     */
    async updateVisibility(sourceId: string, visibility: VisibilityType): Promise<boolean> {
        try {
            await ragApi.updateSourceVisibility(sourceId, visibility);
            // Update local state
            const source = this.sources.find(s => s.id === sourceId);
            if (source) {
                source.visibility = visibility;
                // Trigger reactivity
                this.sources = [...this.sources];
            }
            toast.success(`Source visibility updated to "${visibility}"`);
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to update visibility: ${error.message}`);
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

    // ========== Collection Methods ==========

    /**
     * Load all collections (flat list)
     */
    async loadCollections(): Promise<void> {
        try {
            this.collections = await ragApi.listCollections(false);
        } catch (e) {
            console.error('Failed to load collections:', e);
        }
    }

    /**
     * Load collection tree (nested structure)
     */
    async loadCollectionTree(): Promise<void> {
        try {
            this.collectionTree = await ragApi.listCollections(true);
        } catch (e) {
            console.error('Failed to load collection tree:', e);
        }
    }

    /**
     * Create a new collection
     */
    async createCollection(
        name: string,
        parentId: string | null = null,
        visibility: CollectionVisibility = 'personal'
    ): Promise<boolean> {
        try {
            const collection = await ragApi.createCollection({
                name,
                parent_id: parentId,
                visibility
            });
            toast.success(`Collection "${name}" created`);
            await this.loadCollections();
            await this.loadCollectionTree();
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to create collection: ${error.message}`);
            return false;
        }
    }

    /**
     * Delete a collection
     */
    async deleteCollection(collectionId: string): Promise<boolean> {
        try {
            await ragApi.deleteCollection(collectionId);
            toast.success('Collection deleted');
            await this.loadCollections();
            await this.loadCollectionTree();
            if (this.currentCollectionId === collectionId) {
                this.currentCollectionId = null;
            }
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to delete collection: ${error.message}`);
            return false;
        }
    }

    /**
     * Update a collection
     */
    async updateCollection(
        collectionId: string,
        name?: string,
        visibility?: CollectionVisibility
    ): Promise<boolean> {
        try {
            await ragApi.updateCollection(collectionId, { name, visibility });
            toast.success('Collection updated');
            await this.loadCollections();
            await this.loadCollectionTree();
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to update collection: ${error.message}`);
            return false;
        }
    }

    /**
     * Move a collection to a new parent
     */
    async moveCollection(collectionId: string, newParentId: string | null): Promise<boolean> {
        try {
            await ragApi.moveCollection(collectionId, newParentId);
            toast.success('Collection moved');
            await this.loadCollectionTree();
            return true;
        } catch (e) {
            const error = e as Error;
            toast.error(`Failed to move collection: ${error.message}`);
            return false;
        }
    }

    /**
     * Set current collection for filtering
     */
    setCurrentCollection(collectionId: string | null): void {
        this.currentCollectionId = collectionId;
    }

    /**
     * Get collection by ID
     */
    getCollection(collectionId: string): RAGCollection | undefined {
        return this.collections.find(c => c.id === collectionId);
    }

    /**
     * Ingest file to specific collection
     */
    async ingestFileToCollection(
        file: File,
        collectionId: string | null,
        chunkSize: number = 500,
        chunkOverlap: number = 50,
        visibility: VisibilityType = 'private'
    ): Promise<boolean> {
        this.isUploading = true;
        this.error = null;
        try {
            const result = await ragApi.ingestFileToCollection(
                file, collectionId, chunkSize, chunkOverlap, visibility
            );
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
     * Download a source file
     */
    async downloadSource(sourceId: string): Promise<void> {
        try {
            const source = this.getSource(sourceId);
            if (!source) {
                toast.error('Source not found');
                return;
            }

            const blob = await ragApi.downloadSource(sourceId);

            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = source.name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            toast.success(`Downloaded "${source.name}"`);
        } catch (e) {
            const error = e as Error;
            toast.error(`Download failed: ${error.message}`);
        }
    }

    /**
     * Get sources filtered by current collection
     */
    get currentCollectionSources(): RAGSource[] {
        if (!this.currentCollectionId) return this.sources;
        return this.sources.filter(s =>
            (s as any).collection_id === this.currentCollectionId
        );
    }

    /**
     * Toggle RAG context injection
     */
    toggleRag(): void {
        this.ragEnabled = !this.ragEnabled;
    }

    /**
     * Check if RAG is active (enabled + has selected sources)
     */
    get isRagActive(): boolean {
        return this.ragEnabled && this.selectedSourceIds.length > 0;
    }

    /**
     * Build RAG context from a query
     * Retrieves relevant chunks and formats them for injection into system prompt
     */
    async buildContextFromQuery(query: string): Promise<string | null> {
        if (!this.isRagActive) {
            return null;
        }

        try {
            let chunks: RAGChunk[] = [];
            let contextString = "";

            if (this.advancedMode) {
                // Advanced Pipeline
                const result = await ragApi.advancedRetrieve(
                    query,
                    this.contextBudget,
                    this.hybridRatio,
                    this.selectedSourceIds.length > 0 ? this.selectedSourceIds : null
                );
                chunks = result.chunks;
                // For advanced, the backend assembles the context
                contextString = result.context;
            } else {
                // Standard Retrieval
                chunks = await ragApi.retrieve(query, 5, 0.3);
                if (!chunks || chunks.length === 0) {
                    this.lastRetrievedChunks = [];
                    return null;
                }

                // Build context string locally
                const contextParts: string[] = [
                    '=== RELEVANT KNOWLEDGE ===',
                    '',
                ];

                for (const chunk of chunks) {
                    const source = this.getSource(chunk.source_id);
                    const sourceName = source?.name || 'Unknown Source';
                    contextParts.push(`**Source: ${sourceName}**`);
                    contextParts.push(chunk.content);
                    contextParts.push('');
                }

                contextParts.push('=== END OF KNOWLEDGE ===');
                contextParts.push('');
                contextParts.push('Use the above knowledge to help answer the user\'s question. If the knowledge is relevant, cite the source names in your response.');

                contextString = contextParts.join('\n');
            }

            if (!chunks || chunks.length === 0) {
                this.lastRetrievedChunks = [];
                return null;
            }

            // Store chunks for citation display
            this.lastRetrievedChunks = chunks;

            return contextString;
        } catch (e) {
            console.error('Failed to build RAG context:', e);
            this.lastRetrievedChunks = [];
            return null;
        }
    }

    /**
     * Get formatted citations for display in chat messages
     */
    getCitationsForDisplay(): Citation[] {
        return this.lastRetrievedChunks.map(chunk => {
            const source = this.getSource(chunk.source_id);
            return {
                source_id: chunk.source_id,
                source_name: source?.name || 'Unknown Source',
                score: chunk.score,
                content_preview: chunk.content.length > 200
                    ? chunk.content.slice(0, 200) + '...'
                    : chunk.content
            };
        });
    }

    /**
     * Clear last citations (call after message is saved)
     */
    clearLastCitations(): void {
        this.lastRetrievedChunks = [];
    }
}

export const ragStore = new RAGStore();

