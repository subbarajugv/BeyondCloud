-- RBAC Migration: Add role column to users
-- Run this migration to enable role-based access control

-- Add role column with default 'user'
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user' NOT NULL;

-- Create index for role queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Role values:
-- 'user'       - Basic chat access
-- 'rag_user'   - + RAG features
-- 'agent_user' - + Agent & MCP tools
-- 'admin'      - + User management
-- 'owner'      - Full access

-- Upgrade path to full RBAC (later):
-- CREATE TABLE roles (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(50) UNIQUE NOT NULL,
--     description TEXT,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );
-- 
-- CREATE TABLE user_roles (
--     user_id UUID REFERENCES users(id) ON DELETE CASCADE,
--     role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
--     PRIMARY KEY (user_id, role_id)
-- );
-- 
-- CREATE TABLE permissions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     code VARCHAR(100) UNIQUE NOT NULL,
--     description TEXT
-- );
-- 
-- CREATE TABLE role_permissions (
--     role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
--     permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
--     PRIMARY KEY (role_id, permission_id)
-- );
