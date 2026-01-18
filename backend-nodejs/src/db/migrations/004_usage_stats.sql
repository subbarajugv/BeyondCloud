-- Usage Stats and Agent Sessions Migration
-- Adds usage tracking and persistent agent sessions

-- Usage stats - aggregated analytics per user
CREATE TABLE IF NOT EXISTS usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Time period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- RAG usage
    rag_queries INTEGER DEFAULT 0,
    rag_ingestions INTEGER DEFAULT 0,
    rag_chunks_retrieved INTEGER DEFAULT 0,
    
    -- Agent usage  
    agent_tool_calls INTEGER DEFAULT 0,
    agent_approvals INTEGER DEFAULT 0,
    agent_rejections INTEGER DEFAULT 0,
    
    -- LLM usage
    llm_requests INTEGER DEFAULT 0,
    llm_tokens_input INTEGER DEFAULT 0,
    llm_tokens_output INTEGER DEFAULT 0,
    
    -- MCP usage
    mcp_tool_calls INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint per user per period
    CONSTRAINT unique_user_period UNIQUE (user_id, period_start, period_end)
);

-- Indexes for usage_stats
CREATE INDEX IF NOT EXISTS idx_usage_stats_user_id ON usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_period ON usage_stats(period_start, period_end);

-- Agent sessions - persistent agent state
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Sandbox configuration
    sandbox_path TEXT NOT NULL,
    approval_mode VARCHAR(20) DEFAULT 'require_approval',  -- require_approval, trust_mode
    
    -- State
    is_active BOOLEAN DEFAULT true,
    
    -- Tool execution history (last 100)
    execution_history JSONB DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agent_sessions
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_id ON agent_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_is_active ON agent_sessions(is_active) WHERE is_active = true;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_usage_stats_updated_at ON usage_stats;
CREATE TRIGGER update_usage_stats_updated_at
    BEFORE UPDATE ON usage_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_sessions_updated_at ON agent_sessions;
CREATE TRIGGER update_agent_sessions_updated_at
    BEFORE UPDATE ON agent_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
