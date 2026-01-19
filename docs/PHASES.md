# Implementation Phases

**Version**: 1.0  
**Last Updated**: 2026-01-19

Complete phase breakdown for independent frontend/backend development.

---

## Phase Overview

| Phase | Focus | Duration | Parallel |
|-------|-------|----------|----------|
| 0 | Multi-Backend LLM | 1-2 days | ✅ Completed |
| 1 | Backend Core | 3-5 days | ✅ Completed |
| 2 | Frontend Core | 3-5 days | ✅ Completed |
| 3 | Data Migration | 1-2 days | ✅ Completed |
| 4 | Agents & Tools | 3-5 days | 🚧 In Progress |
| 5 | RAG System | 3-5 days | 🚧 In Progress |
| 6 | Security & Production | 2-3 days | - |

---

## Phase 0: Multi-Backend LLM Integration

**Goal**: Support multiple LLM providers with same interface

### Deliverables
- Provider configuration system
- API key storage per provider
- Provider selector in UI

### API Endpoints

```
GET  /api/providers              - List available providers
POST /api/providers/test         - Test provider connection
GET  /api/models                 - List models for active provider
```

### Supported Providers

| Provider | Base URL |
|----------|----------|
| llama.cpp | `http://localhost:8080/v1` |
| Ollama | `http://localhost:11434/v1` |
| OpenAI | `https://api.openai.com/v1` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` |
| Groq | `https://api.groq.com/openai/v1` |

---

## Phase 1: Backend Core

**Goal**: Authentication, user management, conversation storage

### API Endpoints - Auth

```
POST /api/auth/register          - Create account
POST /api/auth/login             - Get tokens
POST /api/auth/logout            - Invalidate token
POST /api/auth/refresh           - Refresh access token
POST /api/auth/forgot-password   - Request reset
POST /api/auth/reset-password    - Set new password
GET  /api/auth/me                - Get current user
```

### API Endpoints - Conversations

```
GET    /api/conversations           - List user's conversations
POST   /api/conversations           - Create conversation
GET    /api/conversations/:id       - Get conversation
PUT    /api/conversations/:id       - Update conversation
DELETE /api/conversations/:id       - Delete conversation
```

### API Endpoints - Messages

```
GET    /api/messages/:convId        - Get messages
POST   /api/messages                - Create message
DELETE /api/messages/:id            - Delete message
```

### API Endpoints - Chat

```
POST /api/chat/completions          - Chat with LLM (streaming)
```

### API Endpoints - Settings

```
GET  /api/settings                  - Get user settings
PUT  /api/settings                  - Update settings
```

### Database Tables

- `users` - User accounts
- `conversations` - Chat conversations
- `messages` - Chat messages
- `refresh_tokens` - JWT refresh tokens
- `user_settings` - User preferences

---

## Phase 2: Frontend Core

**Goal**: Auth UI, chat integration with backend API

> **Can develop in parallel with Phase 1** - use mock API responses

### Components to Build

- Login page (`/login`)
- Register page (`/register`)
- Forgot password page (`/forgot-password`)
- Auth store (`auth.svelte.ts`)
- Protected route wrapper
- User menu component

### API Client

Single client for all backend calls - see `api-contract.md`

---

## Phase 3: Data Migration

**Goal**: Move from IndexedDB to backend API

### Changes

- Replace `DatabaseStore` with API calls
- Update `chat.svelte.ts` to use backend
- Update `settings.svelte.ts` to sync
- Remove Dexie dependency

---

## Phase 4: Agents & Tools

**Goal**: Agent execution loop with tool calling

### API Endpoints - Agent

```
POST /api/agent/run                 - Start agent task
GET  /api/agent/:id/status          - Get status (SSE stream)
POST /api/agent/:id/stop            - Stop agent
POST /api/agent/:id/approve         - Approve action (HITL)
```

### API Endpoints - Tools

```
GET    /api/tools                   - List available tools
GET    /api/tools/:name             - Get tool schema
POST   /api/tools/:name/execute     - Execute tool manually
```

### See: [AGENT_CONTRACT.md](AGENT_CONTRACT.md)

---

## Phase 5: RAG System

**Goal**: Document ingestion and retrieval

> **Can develop in parallel with Phase 4**

### API Endpoints - Ingestion

```
POST   /api/rag/ingest              - Start ingestion
GET    /api/rag/ingest/:jobId       - Job status
DELETE /api/rag/ingest/:jobId       - Cancel job
```

### API Endpoints - Data Sources

```
GET    /api/rag/sources             - List sources
POST   /api/rag/sources             - Create source
DELETE /api/rag/sources/:id         - Delete source
PUT    /api/rag/sources/:id/access  - Update access
```

### API Endpoints - Query

```
POST /api/rag/query                 - RAG query (with generation)
POST /api/rag/retrieve              - Retrieve only
```

### See: [RAG_CONTRACT.md](RAG_CONTRACT.md)

---

## Phase 6: Security & Production

**Goal**: Hardened production deployment

### Architecture (Same-Origin - No CORS)

```
                    Internet
                        │
                        ▼
              ┌─────────────────┐
              │  Nginx/Caddy    │  ← SSL termination
              │  Reverse Proxy  │  ← Rate limiting
              └─────────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
    /                           /api/*
    │                               │
┌─────────────────┐       ┌─────────────────┐
│    Frontend     │       │     Backend     │
│   (Static)      │       │   (API Only)    │
│   Port 3000     │       │   Port 4000     │
└─────────────────┘       └─────────────────┘
```

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=chat:10m rate=10r/s;
    
    # Auth endpoints - strict rate limit
    location /api/auth/ {
        limit_req zone=auth burst=10 nodelay;
        proxy_pass http://localhost:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Chat endpoints - allow bursts
    location /api/chat/ {
        limit_req zone=chat burst=20;
        proxy_pass http://localhost:4000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;  # SSE streaming
    }
    
    # All other API endpoints
    location /api/ {
        limit_req zone=api burst=50;
        proxy_pass http://localhost:4000;
    }
    
    # Frontend (static files)
    location / {
        root /var/www/frontend/build;
        try_files $uri $uri/ /index.html;
    }
}
```

### Rate Limits

| Endpoint | Limit | Burst |
|----------|-------|-------|
| `/api/auth/login` | 5/sec | 10 |
| `/api/auth/register` | 2/sec | 5 |
| `/api/auth/forgot-password` | 1/sec | 3 |
| `/api/chat/completions` | 10/sec | 20 |
| `/api/rag/ingest` | 2/sec | 5 |
| All other API | 30/sec | 50 |

### Security Headers

```nginx
# Add to server block
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

### Why No CORS?

| With CORS | Same-Origin (Our Approach) |
|-----------|---------------------------|
| Complex configuration | No CORS config needed |
| Preflight requests | No preflight overhead |
| CORS headers exposed | Simpler headers |
| Cookie complications | Cookies work naturally |

**Same-origin = Frontend and API on same domain via reverse proxy**

---

## Alternative: Cross-Origin Deployment (Local Frontend + Cloud Backend)

If you can't use same-origin (e.g., local development against cloud API):

### Architecture

```
Local Machine                           Cloud
─────────────                           ─────
┌─────────────────┐                    ┌─────────────────┐
│ Frontend        │ ──── HTTPS ────▶  │ Backend API     │
│ localhost:5173  │                    │ api.example.com │
└─────────────────┘                    └─────────────────┘
```

### Security WITHOUT CORS

**Use API Key + Origin Validation instead of CORS:**

```typescript
// Backend middleware - NO CORS headers
function securityMiddleware(req, res, next) {
  // 1. Validate API key (from header)
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || !isValidApiKey(apiKey)) {
    return res.status(401).json({ error: 'Invalid API key' });
  }
  
  // 2. Validate origin (optional allowlist)
  const origin = req.headers['origin'];
  const allowedOrigins = ['http://localhost:5173', 'https://myapp.com'];
  if (origin && !allowedOrigins.includes(origin)) {
    return res.status(403).json({ error: 'Origin not allowed' });
  }
  
  // 3. Rate limit by API key
  if (isRateLimited(apiKey)) {
    return res.status(429).json({ error: 'Rate limited' });
  }
  
  next();
}
```

### Frontend Configuration

```typescript
// Frontend API client
const api = {
  baseUrl: 'https://api.example.com',
  apiKey: import.meta.env.VITE_API_KEY, // Per-user or per-app key
  
  async fetch(endpoint, options = {}) {
    return fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        'Authorization': `Bearer ${getAccessToken()}`,
        ...options.headers
      }
    });
  }
};
```

### Security Layers for Cross-Origin

| Layer | Protection |
|-------|------------|
| **API Key** | Identifies the client app |
| **JWT Token** | Authenticates the user |
| **Origin Validation** | Allowlist of frontends |
| **Rate Limiting** | Per API key limits |
| **IP Allowlist** | (Optional) Restrict IPs |

### Why This Works Without CORS

1. **No browser CORS enforcement** - API key auth bypasses CORS
2. **Server-side validation** - Origin checked on server
3. **Rate limiting per key** - Prevents abuse
4. **JWT still required** - User auth unchanged

### Deployment Scenarios

| Scenario | Approach |
|----------|----------|
| Production (frontend + backend same server) | Same-origin (no CORS) |
| Production (frontend CDN + backend cloud) | Same-origin via reverse proxy |
| Development (local frontend + cloud backend) | API key + origin validation |
| Multiple frontends (web + mobile) | API key per app |

### Cloudflare/Nginx Proxy Option

Even with separate deployments, you can achieve same-origin:

```
yourapp.com/          → CDN/Vercel (frontend)
yourapp.com/api/*     → Cloud backend

Both on same domain = Same origin = No CORS
```

---

## Recommendation

| Use Case | Recommendation |
|----------|----------------|
| **Production** | Same-origin via reverse proxy |
| **Development** | API key auth OR Vite proxy |
| **Multi-tenant** | API key per tenant |

---

## RBAC Integration

**All phases must respect:** [RBAC_CONTRACT.md](RBAC_CONTRACT.md)

| Phase | RBAC Considerations |
|-------|---------------------|
| 1 | User roles table, permission middleware |
| 2 | Role-based UI (hide admin features) |
| 4 | Agent access control |
| 5 | Data source access control |

---

## API Summary

### All Endpoints (Complete List)

```
# Auth
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
POST   /api/auth/forgot-password
POST   /api/auth/reset-password
GET    /api/auth/me

# Conversations
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/:id
PUT    /api/conversations/:id
DELETE /api/conversations/:id

# Messages
GET    /api/messages/:convId
POST   /api/messages
DELETE /api/messages/:id

# Chat (LLM)
POST   /api/chat/completions
GET    /api/providers
POST   /api/providers/test
GET    /api/models

# Settings
GET    /api/settings
PUT    /api/settings

# Agent
POST   /api/agent/run
GET    /api/agent/:id/status
POST   /api/agent/:id/stop
POST   /api/agent/:id/approve

# Tools
GET    /api/tools
GET    /api/tools/:name
POST   /api/tools/:name/execute

# RAG
POST   /api/rag/ingest
GET    /api/rag/ingest/:jobId
DELETE /api/rag/ingest/:jobId
GET    /api/rag/sources
POST   /api/rag/sources
DELETE /api/rag/sources/:id
PUT    /api/rag/sources/:id/access
POST   /api/rag/query
POST   /api/rag/retrieve

# Admin (RBAC)
GET    /api/admin/users
PUT    /api/admin/users/:id/roles
GET    /api/admin/roles
```

---

## Contract Documents

| Document | Purpose |
|----------|---------|
| [CONTRACT.md](CONTRACT.md) | Core API contract |
| [AGENT_CONTRACT.md](AGENT_CONTRACT.md) | Agent sub-contracts |
| [RAG_CONTRACT.md](RAG_CONTRACT.md) | RAG sub-contracts |
| [RBAC_CONTRACT.md](RBAC_CONTRACT.md) | Access control |
| [API_OVERVIEW.md](API_OVERVIEW.md) | Detailed endpoint specs |
