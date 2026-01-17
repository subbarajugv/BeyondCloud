# Adapting llama.cpp WebUI for User Authentication

## Overview

This plan outlines how to adapt the llama.cpp WebUI (built with Svelte 5) to add user authentication and login functionality. The current WebUI is designed for single-user local use with optional API key protection. We'll transform it into a multi-user system with proper authentication.

## Related Documents

| Document | Description |
|----------|-------------|
| [component-architecture.md](component-architecture.md) | Independent components diagram, parallel development strategy |
| [api-contract.md](api-contract.md) | Complete API specification for frontend/backend |
| [multi-backend-pros-cons.md](multi-backend-pros-cons.md) | Multi-provider support analysis |


## Current Architecture Analysis

### Frontend Stack
- **Framework**: Svelte 5 with SvelteKit (SSR/SPA hybrid)
- **State Management**: Reactive stores using Svelte 5 runes (`$state`, `$derived`)
- **Persistence**: IndexedDB via Dexie for client-side storage
- **Styling**: TailwindCSS v4 + bits-ui components
- **API Communication**: Fetch API with streaming support

### Key Components
1. **Stores** (`src/lib/stores/`):
   - `chat.svelte.ts` - Conversation and message management
   - `settings.svelte.ts` - User preferences and configuration
   - `server.svelte.ts` - Server connection state
   - `database.ts` - IndexedDB wrapper for local persistence

2. **Services** (`src/lib/services/`):
   - `chat.ts` - API communication with llama.cpp server
   - `slots.ts` - Server resource monitoring

3. **Routes** (`src/routes/`):
   - `+layout.svelte` - Root layout with sidebar and API key handling
   - `+page.svelte` - Home/chat interface
   - `/chat/[id]` - Individual conversation view

### Current Authentication
- **API Key Only**: Optional Bearer token in `Authorization` header
- **Client-Side Storage**: All data stored in browser's IndexedDB
- **No User Concept**: Single-user assumption

---

## User Review Required

> [!IMPORTANT]
> **Multi-User Data Isolation**: This plan assumes you want each user to have their own isolated chat history and settings. All conversations will be stored server-side and associated with user accounts.

> [!WARNING]
> **Breaking Change**: Moving from client-side (IndexedDB) to server-side storage means existing local chat histories will not automatically migrate. You'll need a separate migration strategy if preserving existing data is important.

> [!CAUTION]
> **Backend Choice**: This plan requires building a custom backend API layer (Node.js/Express, Python/FastAPI, or similar) between the WebUI and llama.cpp server. The llama.cpp server itself doesn't handle user authentication natively.

---

## Proposed Changes

### Backend (New Service Layer)

You'll need to create a new backend service that sits between the WebUI and llama.cpp server. This handles authentication, user management, and data persistence.

#### [NEW] Authentication API Service

**Technology Options**:
- **Node.js + Express**: Matches frontend JavaScript ecosystem
- **Python + FastAPI**: Good for ML/AI projects
- **Go**: High performance, good for proxying

**Core Responsibilities**:
1. User authentication (JWT tokens)
2. Session management
3. Conversation storage (PostgreSQL/MySQL/MongoDB)
4. Proxy requests to llama.cpp server
5. Per-user API key management

**Required Endpoints**:

```
# Authentication (Core)
POST   /api/auth/register          - User registration (with email verification)
POST   /api/auth/login             - User login (returns access + refresh tokens)
POST   /api/auth/logout            - Invalidate session (blacklist tokens)
POST   /api/auth/refresh           - Refresh access token using refresh token
GET    /api/auth/me                - Get current user info

# Password Management
POST   /api/auth/forgot-password   - Request password reset (sends email)
POST   /api/auth/reset-password    - Reset password with token
POST   /api/auth/change-password   - Change password (authenticated)

# Email Verification
POST   /api/auth/verify-email      - Verify email with token
POST   /api/auth/resend-verification - Resend verification email

# Security
POST   /api/auth/revoke-all        - Revoke all user sessions
GET    /api/auth/sessions          - List active sessions
DELETE /api/auth/sessions/:id      - Revoke specific session

# Conversations
GET    /api/conversations          - List user's conversations
POST   /api/conversations          - Create conversation
GET    /api/conversations/:id      - Get conversation details
PUT    /api/conversations/:id      - Update conversation
DELETE /api/conversations/:id      - Delete conversation

# Messages
GET    /api/messages/:convId       - Get messages for conversation
POST   /api/messages               - Create message
PUT    /api/messages/:id           - Update message
DELETE /api/messages/:id           - Delete message

# Settings
GET    /api/settings               - Get user settings
PUT    /api/settings               - Update user settings

# llama.cpp Proxy
POST   /api/chat/completions       - Proxy to llama.cpp (with auth)
GET    /api/props                  - Proxy to llama.cpp /props
```

**Database Schema** (Example for PostgreSQL):

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- USERS TABLE (Enhanced with security fields)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Email verification
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    
    -- Account security
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    
    -- Metadata
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- EMAIL VERIFICATION TOKENS
-- ============================================
CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,  -- 24 hours
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASSWORD RESET TOKENS
-- ============================================
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,  -- Store hashed, not plain
    expires_at TIMESTAMP NOT NULL,      -- 1 hour
    used_at TIMESTAMP,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- REFRESH TOKENS (JWT Rotation)
-- ============================================
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    device_info TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP NOT NULL,  -- 7-30 days
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- USER SESSIONS
-- ============================================
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_id UUID REFERENCES refresh_tokens(id) ON DELETE CASCADE,
    device_name VARCHAR(255),
    browser VARCHAR(100),
    os VARCHAR(100),
    ip_address VARCHAR(45),
    is_current BOOLEAN DEFAULT FALSE,
    last_active_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TOKEN BLACKLIST (For secure logout)
-- ============================================
CREATE TABLE token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    blacklisted_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- CONVERSATIONS & MESSAGES
-- ============================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    curr_node UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    last_modified TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conv_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT,
    type VARCHAR(20) DEFAULT 'text',
    thinking TEXT,
    tool_calls TEXT,
    model VARCHAR(100),
    timestamp BIGINT NOT NULL,
    extra JSONB
);

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}'
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_email_verification_token ON email_verification_tokens(token);
CREATE INDEX idx_password_reset_user ON password_reset_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_blacklist_jti ON token_blacklist(token_jti);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_messages_conv ON messages(conv_id);
CREATE INDEX idx_messages_parent ON messages(parent_id);

-- Cleanup function for expired tokens (run via cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_tokens() RETURNS void AS $$
BEGIN
    DELETE FROM email_verification_tokens WHERE expires_at < NOW();
    DELETE FROM password_reset_tokens WHERE expires_at < NOW();
    DELETE FROM refresh_tokens WHERE expires_at < NOW();
    DELETE FROM token_blacklist WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
```

---

### Frontend Modifications

#### [NEW] [auth.svelte.ts](file:///home/subba/llama.cpp/tools/server/webui/src/lib/stores/auth.svelte.ts)

New authentication store for managing user state:

```typescript
class AuthStore {
  user = $state<User | null>(null);
  token = $state<string | null>(null);
  isAuthenticated = $derived(this.user !== null);
  isLoading = $state(false);

  async login(email: string, password: string): Promise<void>
  async logout(): Promise<void>
  async register(email: string, password: string): Promise<void>
  async checkAuth(): Promise<void>
  async refreshToken(): Promise<void>
}
```

#### [NEW] [api.ts](file:///home/subba/llama.cpp/tools/server/webui/src/lib/services/api.ts)

Centralized API client with authentication:

```typescript
class ApiClient {
  private getHeaders(): HeadersInit
  async get<T>(endpoint: string): Promise<T>
  async post<T>(endpoint: string, data: unknown): Promise<T>
  async put<T>(endpoint: string, data: unknown): Promise<T>
  async delete<T>(endpoint: string): Promise<T>
}
```

#### [NEW] Login/Register Pages

- `src/routes/login/+page.svelte` - Login form
- `src/routes/register/+page.svelte` - Registration form
- `src/lib/components/auth/LoginForm.svelte` - Reusable login component
- `src/lib/components/auth/RegisterForm.svelte` - Reusable register component

#### [MODIFY] [+layout.svelte](file:///home/subba/llama.cpp/tools/server/webui/src/routes/+layout.svelte)

Add authentication check and redirect logic:

```svelte
<script lang="ts">
  import { authStore } from '$lib/stores/auth.svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  $effect(() => {
    authStore.checkAuth();
  });

  $effect(() => {
    const publicRoutes = ['/login', '/register'];
    const isPublicRoute = publicRoutes.includes(page.route.id || '');
    
    if (!authStore.isAuthenticated && !isPublicRoute) {
      goto('/login');
    } else if (authStore.isAuthenticated && isPublicRoute) {
      goto('/');
    }
  });
</script>
```

#### [MODIFY] [database.ts](file:///home/subba/llama.cpp/tools/server/webui/src/lib/stores/database.ts)

Replace IndexedDB with API calls:

```typescript
// Before: Direct IndexedDB operations
await db.conversations.add(conversation);

// After: API calls to backend
await apiClient.post('/api/conversations', conversation);
```

**Key Changes**:
- Remove Dexie/IndexedDB dependency
- Replace all database operations with API calls
- Add error handling for network failures
- Implement optimistic updates for better UX

#### [MODIFY] [chat.ts](file:///home/subba/llama.cpp/tools/server/webui/src/lib/services/chat.ts)

Update API endpoints to use authenticated backend:

```typescript
// Before: Direct call to llama.cpp
fetch(`./v1/chat/completions`, {
  headers: { Authorization: `Bearer ${apiKey}` }
})

// After: Call through authenticated backend
fetch(`/api/chat/completions`, {
  headers: { Authorization: `Bearer ${authStore.token}` }
})
```

#### [MODIFY] [settings.svelte.ts](file:///home/subba/llama.cpp/tools/server/webui/src/lib/stores/settings.svelte.ts)

Sync settings with backend instead of localStorage:

```typescript
// Before: localStorage.setItem('config', JSON.stringify(this.config))
// After: await apiClient.put('/api/settings', this.config)
```

#### [NEW] User Profile Component

`src/lib/components/app/UserProfile.svelte` - Display user info and logout button in sidebar

---

### Configuration Changes

#### [MODIFY] [svelte.config.js](file:///home/subba/llama.cpp/tools/server/webui/svelte.config.js)

Configure API proxy for development:

```javascript
const config = {
  kit: {
    adapter: adapter(),
    alias: {
      $lib: './src/lib'
    },
    // Proxy API requests to backend during development
    vite: {
      server: {
        proxy: {
          '/api': {
            target: 'http://localhost:3000', // Your backend URL
            changeOrigin: true
          }
        }
      }
    }
  }
};
```

---

## Implementation Phases

### Phase 0: Multi-Backend LLM Integration (START HERE)
> **Priority**: Do this first - enables flexibility before adding auth complexity

1. Create provider configuration system
2. Make base URL configurable in settings
3. Add API key storage per provider
4. Implement provider selector in UI
5. Test with all OpenAI-compatible backends

**Supported Providers (OpenAI-Compatible):**

| Provider | Base URL | Notes |
|----------|----------|-------|
| llama.cpp | `http://localhost:8080/v1` | Local, default |
| Ollama | `http://localhost:11434/v1` | Local |
| OpenAI | `https://api.openai.com/v1` | Cloud, paid |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | Cloud, free tier |
| Groq | `https://api.groq.com/openai/v1` | Cloud, fast |
| Azure OpenAI | `https://{resource}.openai.azure.com/openai/deployments/{deployment}` | Enterprise |
| Together AI | `https://api.together.xyz/v1` | Cloud |
| vLLM | `http://localhost:8000/v1` | Self-hosted |

**Code Changes Required:**

```typescript
// src/lib/stores/settings.svelte.ts - Add provider config
interface ProviderConfig {
  id: string;
  name: string;
  baseUrl: string;
  apiKey?: string;
  models: string[];
  isDefault?: boolean;
}

// Default providers
const defaultProviders: ProviderConfig[] = [
  { id: 'llama.cpp', name: 'llama.cpp (Local)', baseUrl: 'http://localhost:8080/v1', models: ['default'] },
  { id: 'ollama', name: 'Ollama (Local)', baseUrl: 'http://localhost:11434/v1', models: [] },
  { id: 'openai', name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini'] },
  { id: 'gemini', name: 'Google Gemini', baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', models: ['gemini-2.0-flash', 'gemini-1.5-pro'] },
  { id: 'groq', name: 'Groq', baseUrl: 'https://api.groq.com/openai/v1', models: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768'] },
];
```

```typescript
// src/lib/services/chat.ts - Update to use provider config
const response = await fetch(`${activeProvider.baseUrl}/chat/completions`, {
  headers: {
    'Content-Type': 'application/json',
    ...(activeProvider.apiKey ? { Authorization: `Bearer ${activeProvider.apiKey}` } : {})
  },
  body: JSON.stringify({ model: activeProvider.selectedModel, messages, stream })
});
```

**Estimated Time: 1-2 days**

---

### Phase 1: Backend Setup
1. Choose backend technology (Node.js/Python/Go)
2. Set up database (PostgreSQL recommended)
3. Implement authentication endpoints
4. Implement conversation/message CRUD APIs
5. Add LLM proxy endpoint (routes to user's selected provider)
6. Test all endpoints with Postman/curl

### Phase 2: Frontend Authentication
> **Can develop in parallel with Phase 1 using API contract**

1. Create auth store
2. Build login/register pages
3. Add route protection in `+layout.svelte`
4. Implement JWT token refresh logic
5. Add user profile component

### Phase 3: Data Migration
1. Replace IndexedDB with API calls in `database.ts`
2. Update `chat.svelte.ts` to use new API
3. Update `settings.svelte.ts` to sync with backend
4. Remove Dexie dependency
5. Test conversation creation/loading

### Phase 4: Testing & Polish
1. Test authentication flow
2. Test multi-user isolation
3. Add loading states
4. Add error handling
5. Implement session persistence
6. Add "Remember me" functionality

### Phase 5: MCP Integration
> **Status**: In Progress - implement external tool server connections

1. Install MCP SDK (`@modelcontextprotocol/sdk` for Node.js or `mcp` for Python)
2. Implement MCPService with real implementation
3. Add MCP server configuration to Settings UI
4. Implement tool discovery (`listTools`)
5. Implement tool execution (`callTool`)
6. Convert MCP tools to OpenAI function format
7. Integrate with chat flow (tool calls → MCP → LLM)

**MCP Service Interface:**
```typescript
interface MCPService {
  listServers(): Promise<MCPServer[]>;
  addServer(config: MCPServerConfig): Promise<void>;
  removeServer(id: string): Promise<void>;
  listTools(serverId?: string): Promise<MCPTool[]>;
  callTool(serverId: string, toolName: string, args: any): Promise<any>;
  getOpenAITools(): Promise<OpenAITool[]>;
}
```

### Phase 6: Agent & Tools System (Completion)
> **Status**: Partial - core done, add remaining tools

1. ✅ Agent execution loop
2. ✅ Tool registry with file/command tools
3. ✅ Tool approval UI
4. ✅ OTel-compatible tracing
5. [ ] Web search tool
6. [ ] Code interpreter tool
7. [ ] HTTP request tool

### Phase 7: Production Deployment (LAST)
1. Set up reverse proxy (Nginx or Caddy)
2. Configure same-origin deployment (eliminates CORS)
3. SSL/TLS certificate setup
4. Environment variable configuration
5. Database connection pooling
6. Logging and monitoring setup
7. Backup and recovery procedures


---

### Phase 7: Agent & Tools System
> **Purpose**: Enable LLM agents with tool calling capabilities

**Backend Components:**

1. **Agent Service** - Orchestrates agent execution loop
2. **Tool Registry** - Manages available tools
3. **Execution Engine** - Runs tools and handles results

**API Endpoints:**

```
POST   /api/agent/run           - Start agent with task
GET    /api/agent/:id/status    - Get agent run status (streaming)
POST   /api/agent/:id/stop      - Stop running agent
GET    /api/tools               - List available tools
GET    /api/tools/:name         - Get tool schema
POST   /api/tools/:name/execute - Execute tool manually
```

**Agent Service Interface:**

```typescript
interface AgentService {
  // Run agent with task
  run(task: string, options: AgentOptions): AsyncGenerator<AgentEvent>;
  
  // Stop running agent
  stop(agentId: string): Promise<void>;
  
  // Get status
  getStatus(agentId: string): Promise<AgentStatus>;
}

interface AgentOptions {
  model: string;
  provider: string;
  tools: string[];           // Tool names to enable
  maxIterations: number;     // Prevent infinite loops
  timeout: number;           // Max execution time
}

interface AgentEvent {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'message' | 'error' | 'done';
  data: any;
  timestamp: number;
}
```

**Tool Registry Interface:**

```typescript
interface ToolRegistry {
  // Register a tool
  register(tool: Tool): void;
  
  // List all tools
  list(): Tool[];
  
  // Get tool by name
  get(name: string): Tool | null;
  
  // Execute tool
  execute(name: string, args: any): Promise<ToolResult>;
  
  // Convert to OpenAI function format
  toOpenAIFormat(): OpenAITool[];
}

interface Tool {
  name: string;
  description: string;
  parameters: JSONSchema;
  execute: (args: any) => Promise<any>;
}
```

**Agent Execution Loop:**

```
┌─────────────────────────────────────────┐
│ 1. Receive task from user               │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ 2. Send to LLM with available tools     │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ 3. LLM responds                         │
│    - Final answer? → Return to user     │
│    - Tool call? → Continue to step 4    │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ 4. Execute tool, get result             │
│    Stream: { type: "tool_call", ... }   │
│    Stream: { type: "tool_result", ... } │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ 5. Add tool result to messages          │
│    Go back to step 2                    │
└─────────────────────────────────────────┘
```

**Built-in Tools (Examples):**

| Tool | Description |
|------|-------------|
| `web_search` | Search the web |
| `code_interpreter` | Run Python code |
| `file_read` | Read file contents |
| `file_write` | Write to file |
| `http_request` | Make HTTP calls |

**Frontend Integration:**

```svelte
<!-- Display tool calls in chat -->
{#if message.type === 'tool_call'}
  <div class="tool-call">
    <span class="icon">🔧</span>
    <span class="name">{message.data.name}</span>
    <span class="status">{message.data.status}</span>
  </div>
{/if}

{#if message.type === 'tool_result'}
  <div class="tool-result">
    <pre>{JSON.stringify(message.data.result, null, 2)}</pre>
  </div>
{/if}
```

**Implementation Steps:**

1. Create Agent Service with execution loop
2. Create Tool Registry
3. Implement built-in tools
4. Add agent API endpoints
5. Integrate with MCP for external tools
6. Add frontend visualization
7. Add agent configuration UI


#### Nginx Reverse Proxy Configuration (Recommended)

```nginx
# /etc/nginx/sites-available/llamacpp-auth
server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Frontend (Svelte) - serves static files or dev server
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API - all /api/* requests
    location /api {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests (streaming)
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # llama.cpp server (optional direct access)
    location /llama {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        
        # SSE/Streaming support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
```

#### Caddy Alternative (Simpler, Auto-SSL)

```caddyfile
# /etc/caddy/Caddyfile
yourdomain.com {
    # Frontend
    reverse_proxy / localhost:5173

    # Backend API
    reverse_proxy /api/* localhost:3000

    # llama.cpp (optional)
    reverse_proxy /llama/* localhost:8080
}

---

## Verification Plan

### Backend Verification

**Unit Tests** (if using Node.js + Jest):
```bash
# Test authentication endpoints
npm test -- auth.test.js

# Test conversation CRUD
npm test -- conversations.test.js

# Test message operations
npm test -- messages.test.js
```

**Integration Tests**:
```bash
# Test full authentication flow
npm test -- integration/auth-flow.test.js

# Test conversation creation and retrieval
npm test -- integration/conversation-flow.test.js
```

**Manual API Testing**:
1. Register a new user: `POST /api/auth/register`
2. Login: `POST /api/auth/login` (verify JWT returned)
3. Create conversation: `POST /api/conversations` (with JWT)
4. Send message: `POST /api/chat/completions` (verify proxied to llama.cpp)
5. Logout: `POST /api/auth/logout`
6. Verify token invalidated

### Frontend Verification

**Manual Browser Testing**:
1. Navigate to `http://localhost:5173` (or dev server URL)
2. Verify redirect to `/login` when not authenticated
3. Register new account
4. Verify redirect to home page after registration
5. Create a new conversation
6. Send a message and verify AI response
7. Logout and verify redirect to login
8. Login again and verify conversations persisted
9. Open in incognito window, verify separate user isolation

**Multi-User Testing**:
1. Create two user accounts (User A and User B)
2. Login as User A, create conversations
3. Logout, login as User B
4. Verify User B cannot see User A's conversations
5. Create conversations as User B
6. Logout, login as User A again
7. Verify User A's conversations still exist and User B's are not visible

**Build Verification**:
```bash
cd tools/server/webui
npm run build
# Verify no build errors
# Verify bundle size is reasonable
```

---

## Migration Notes

### For Existing Users

If you have users with existing chat histories in IndexedDB, you'll need a migration tool:

1. **Export Tool**: Create a page that exports IndexedDB data to JSON
2. **Import API**: Add backend endpoint to import conversations
3. **Migration Flow**:
   - User logs in for first time
   - Detect local IndexedDB data
   - Prompt user to migrate
   - Export and upload to backend
   - Clear local storage after successful migration

### Environment Variables

Backend `.env` file:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/llamacpp_chat
JWT_SECRET=your-secret-key-here
JWT_EXPIRY=24h
LLAMA_CPP_URL=http://localhost:8080
PORT=3000
```

Frontend `.env` file:
```env
PUBLIC_API_URL=http://localhost:3000/api
```

---

## Security Considerations

### Password Security

| Policy | Value | Rationale |
|--------|-------|-----------|
| Min length | 8 characters | NIST recommendation |
| Hashing | Argon2id or bcrypt (cost 12) | Memory-hard, resistant to GPU attacks |
| Breach check | Check against HaveIBeenPwned API | Prevent known compromised passwords |
| History | Store last 5 hashes | Prevent password reuse |

**Implementation:**
```javascript
// Password hashing with bcrypt
const BCRYPT_ROUNDS = 12;
const hash = await bcrypt.hash(password, BCRYPT_ROUNDS);

// Password validation
const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
```

### Rate Limiting

| Endpoint | Limit | Window | Action on Exceed |
|----------|-------|--------|------------------|
| `/auth/login` | 5 attempts | 15 min | Lock account 30 min |
| `/auth/register` | 3 requests | 1 hour | Block IP |
| `/auth/forgot-password` | 3 requests | 1 hour | Silently ignore |
| `/auth/reset-password` | 5 attempts | 15 min | Invalidate token |
| `/chat/completions` | 60 requests | 1 min | 429 response |
| All endpoints | 100 requests | 1 min | 429 response |

### JWT Token Security

**Access Token:**
- Expiry: 15 minutes
- Storage: Memory only (not localStorage)
- Contains: user_id, email, jti (unique ID)

**Refresh Token:**
- Expiry: 7 days (30 days with "Remember me")
- Storage: HTTP-only, Secure, SameSite=Strict cookie
- Rotation: Issue new refresh token on each use
- Store hash in database for revocation

**Token Structure:**
```javascript
// Access token payload
{
  sub: userId,
  email: userEmail,
  jti: uniqueTokenId,  // For blacklisting
  iat: issuedAt,
  exp: expiresAt
}
```

### Account Security

| Feature | Implementation |
|---------|---------------|
| Account lockout | Lock after 5 failed attempts for 30 minutes |
| Session limit | Max 5 active sessions per user |
| Suspicious login | Email alert on new device/location |
| Password reset | Token valid for 1 hour, single use |
| Email verification | Required before full access |

### API Security

1. **CORS Configuration:**
```javascript
const corsOptions = {
  origin: process.env.FRONTEND_URL,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
};
```

2. **Security Headers:**
```javascript
// Use helmet.js
app.use(helmet());
app.use(helmet.contentSecurityPolicy({...}));
app.use(helmet.hsts({ maxAge: 31536000 }));
```

3. **Input Validation:**
- Sanitize all user inputs
- Use parameterized queries (prevent SQL injection)
- Validate email format server-side
- Limit payload sizes (1MB max)

4. **HTTPS:**
- Enforce HTTPS in production
- HSTS header with long max-age
- Redirect HTTP to HTTPS

### Password Reset Flow (Secure)

```
1. User requests reset → POST /auth/forgot-password
2. Server generates secure token (32 bytes, crypto.randomBytes)
3. Store HASH of token in database (not plain token)
4. Send email with plain token in URL
5. User clicks link → Frontend extracts token
6. User submits new password + token → POST /auth/reset-password
7. Server hashes submitted token, compares with stored hash
8. If match AND not expired AND not used:
   - Update password
   - Mark token as used
   - Invalidate all refresh tokens (force re-login)
   - Send confirmation email
```

### Logout Flow (Secure)

```
1. User clicks logout
2. Add access token JTI to blacklist table
3. Delete refresh token from database
4. Clear HTTP-only cookie
5. Client clears access token from memory
```

---

## Alternative Approaches

### Option 1: Simpler Shared-Key Authentication
Instead of full user accounts, use a shared access key:
- Single "admin" password for access
- All users share same conversations
- Simpler to implement but no user isolation

### Option 2: OAuth Integration
Use third-party authentication (Google, GitHub):
- Less password management
- Better security
- Requires OAuth provider setup

### Option 3: Keep Client-Side Storage
Minimal changes to current architecture:
- Add login page that just validates credentials
- Keep IndexedDB for storage
- Each user uses different browser profile
- No server-side conversation storage
