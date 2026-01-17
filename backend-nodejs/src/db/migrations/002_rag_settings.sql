-- RAG Settings Migration
-- Per-user RAG configuration options

CREATE TABLE IF NOT EXISTS rag_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Chunking options
    chunk_size INT DEFAULT 500,
    chunk_overlap INT DEFAULT 50,
    use_sentence_boundary BOOLEAN DEFAULT true,
    
    -- Reranking options
    reranker_model VARCHAR(100) DEFAULT 'cross-encoder/ms-marco-MiniLM-L-6-v2',
    rerank_top_k INT DEFAULT 5,
    min_score FLOAT DEFAULT 0.3,
    use_reranking BOOLEAN DEFAULT true,
    use_hybrid_search BOOLEAN DEFAULT true,
    bm25_weight FLOAT DEFAULT 0.3,
    
    -- Context assembly
    context_max_tokens INT DEFAULT 4000,
    context_ordering VARCHAR(20) DEFAULT 'score_desc',  -- score_desc, score_asc, position
    
    -- Grounding rules
    require_citations BOOLEAN DEFAULT true,
    max_citations INT DEFAULT 5,
    
    -- RAG system prompt
    rag_system_prompt TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_rag_settings_updated_at ON rag_settings;
CREATE TRIGGER update_rag_settings_updated_at
    BEFORE UPDATE ON rag_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
