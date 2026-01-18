-- Session Management Migration
-- Adds sessions and session_logs tables for tracking and auditing

-- Sessions table - track active login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 of refresh token
    device_info JSONB,                -- {browser, os, ip, user_agent}
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active) WHERE is_active = true;

-- Session logs - audit trail of user actions
CREATE TABLE IF NOT EXISTS session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Log data
    level VARCHAR(10) NOT NULL DEFAULT 'INFO',  -- DEBUG, INFO, WARNING, ERROR
    action VARCHAR(100) NOT NULL,               -- e.g., 'login', 'rag.query', 'agent.execute'
    message TEXT,
    
    -- Context
    trace_id VARCHAR(32),    -- OpenTelemetry trace ID
    span_id VARCHAR(16),     -- OpenTelemetry span ID
    
    -- Request details
    endpoint VARCHAR(200),
    method VARCHAR(10),
    status_code INTEGER,
    duration_ms INTEGER,
    
    -- Extra data
    metadata JSONB,          -- Any additional context
    error TEXT,              -- Error message if applicable
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for session_logs
CREATE INDEX IF NOT EXISTS idx_session_logs_session_id ON session_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_user_id ON session_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_action ON session_logs(action);
CREATE INDEX IF NOT EXISTS idx_session_logs_trace_id ON session_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_created_at ON session_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_logs_level ON session_logs(level) WHERE level IN ('WARNING', 'ERROR');

-- Partition hint (for future scaling - logs can grow large)
-- COMMENT: Consider partitioning session_logs by month for retention policies
