# BeyondCloud API Overview

Complete reference for all API endpoints across both backend services.

## 📡 Architecture

| Service | Port | Responsibility |
|---------|------|----------------|
| **Node.js** | 3000 | Auth, Conversations, Chat, Settings, Providers |
| **Python** | 8001 | RAG, Agents, MCP, Usage Analytics, Health |

---

## Node.js Backend (Port 3000)

### Authentication `/api/auth`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | ❌ | Create new user account |
| POST | `/login` | ❌ | Login, returns JWT + refresh token |
| POST | `/logout` | ✅ | Logout (server-side logging) |
| GET | `/me` | ✅ | Get current user profile |
| PUT | `/profile` | ✅ | Update display name |
| POST | `/refresh` | ❌ | Rotate refresh token, get new JWT |
| POST | `/forgot-password` | ❌ | Request password reset email |
| POST | `/reset-password` | ❌ | Reset password with token |

### Chat `/api/chat`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/completions` | Optional | LLM chat (supports SSE streaming) |

### Conversations `/api/conversations`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | ✅ | List all user conversations |
| POST | `/` | ✅ | Create new conversation |
| GET | `/:id` | ✅ | Get conversation with messages |
| PUT | `/:id` | ✅ | Update name or current_node |
| DELETE | `/:id` | ✅ | Delete conversation + messages |
| POST | `/:id/messages` | ✅ | Add message to conversation |
| PUT | `/:convId/messages/:msgId` | ✅ | Update message content |

### Providers `/api/providers`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | ❌ | List configured LLM providers |
| POST | `/test` | ❌ | Test provider connection |
| GET | `/models` | ❌ | Get models for provider |

### Settings `/api/settings`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | ✅ | Get user settings |
| PUT | `/` | ✅ | Update settings (merge) |

---

## Python Backend (Port 8001)

### Health Checks `/health`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/live` | ❌ | Kubernetes liveness probe |
| GET | `/ready` | ❌ | Kubernetes readiness probe (DB check) |
| GET | `/deep` | ❌ | Deep health: DB + Redis + LLM with latency |

### RAG - Sources `/rag`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/sources` | ✅ | List ingested sources |
| POST | `/ingest` | ✅ | Ingest text content |
| POST | `/ingest/file` | ✅ | Ingest file (PDF, TXT, etc.) |
| DELETE | `/sources/:id` | ✅ | Delete source |
| PUT | `/sources/:id/visibility` | ✅ | Update source visibility |
| GET | `/sources/:id/download` | ✅ | Download original file |

### RAG - Query `/rag`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/retrieve` | ✅ | Vector similarity search |
| POST | `/query` | ✅ | RAG query with LLM generation |

### RAG - Collections `/rag/collections`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | ✅ | List collections |
| POST | `/` | ✅ | Create collection |
| GET | `/:id` | ✅ | Get collection details |
| PUT | `/:id` | ✅ | Update collection |
| DELETE | `/:id` | ✅ | Delete collection |
| POST | `/:id/move` | ✅ | Move sources between collections |

### RAG - Settings `/rag/settings`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | ✅ | Get RAG settings |
| PUT | `/` | ✅ | Update RAG settings |

### Agent `/api/agent`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/set-sandbox` | ✅ | Configure sandbox directory |
| POST | `/set-mode` | ✅ | Set approval mode (auto/manual) |
| GET | `/status` | ✅ | Get agent status + config |
| GET | `/tools` | ✅ | List available tools |
| POST | `/execute` | ✅ | Execute a tool |
| POST | `/approve/:id` | ✅ | Approve pending tool call |
| POST | `/reject/:id` | ✅ | Reject pending tool call |
| GET | `/pending` | ✅ | List pending approvals |
| POST | `/run` | ✅ | Run full agent loop |

### MCP (Model Context Protocol) `/api/mcp`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/servers` | ✅ | List MCP servers |
| POST | `/servers` | ✅ | Add MCP server |
| DELETE | `/servers/:id` | ✅ | Remove MCP server |
| GET | `/tools` | ✅ | List all MCP tools |
| POST | `/tools/call` | ✅ | Execute MCP tool |
| GET | `/tools/openai-format` | ✅ | Get tools as OpenAI schema |

### Usage Analytics `/api/usage`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/stats` | ✅ | Usage statistics summary |
| GET | `/daily` | ✅ | Daily breakdown |

---

## Built-in MCP Tools

11 tools available when agent is enabled:

| Tool | Category | Description |
|------|----------|-------------|
| `read_file` | Filesystem | Read file contents |
| `write_file` | Filesystem | Write to file |
| `list_dir` | Filesystem | List directory contents |
| `search_files` | Filesystem | Glob pattern search |
| `run_command` | Shell | Execute shell command |
| `python_executor` | Code | Run Python code |
| `web_search` | Web | DuckDuckGo search |
| `screenshot` | Web | Capture webpage screenshot |
| `database_query` | Data | Read-only SQL query |
| `think` | Reasoning | Record reasoning step |
| `plan_task` | Planning | Create execution plan |

---

## RBAC Permissions

| Role | RAG | Agent | MCP | Admin |
|------|-----|-------|-----|-------|
| `user` | ❌ | ❌ | ❌ | ❌ |
| `rag_user` | ✅ | ❌ | ❌ | ❌ |
| `agent_user` | ✅ | ✅ | Built-in | ❌ |
| `admin` | ✅ | ✅ | ✅ All | ✅ |

---

## Error Response Format

All endpoints return errors in consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

Common error codes: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `SERVER_ERROR`, `PROVIDER_ERROR`, `LLM_ERROR`

---

## Related Documentation

- [CONTRACT.md](CONTRACT.md) - Core API protocol & guarantees
- [RAG_CONTRACT.md](RAG_CONTRACT.md) - RAG pipeline details
- [AGENT_CONTRACT.md](AGENT_CONTRACT.md) - Agent workflow
- [RBAC_CONTRACT.md](RBAC_CONTRACT.md) - Role-based access control
