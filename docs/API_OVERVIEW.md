# BeyondCloud API Overview

Complete reference for all API endpoints.

## 📡 Architecture

| Service | Port | Responsibility |
|---------|------|----------------|
| **Node.js** | 3000 | Auth, Conversations, Settings |
| **Python** | 8001 | RAG, Agents, MCP, Analytics |

---

## Node.js Backend (Port 3000)

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Get current user |

### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/:id` | Get conversation |
| DELETE | `/api/conversations/:id` | Delete conversation |

### Messages
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations/:id/messages` | List messages |
| POST | `/api/conversations/:id/messages` | Create message |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/completions` | LLM completion |
| POST | `/api/chat/completions/stream` | Streaming completion |

---

## Python Backend (Port 8001)

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/models` | List LLM models |

### RAG - Sources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rag/sources` | List sources |
| POST | `/rag/ingest` | Ingest text |
| POST | `/rag/ingest/file` | Ingest file |
| DELETE | `/rag/sources/:id` | Delete source |
| PUT | `/rag/sources/:id/visibility` | Update visibility |
| GET | `/rag/sources/:id/download` | Download file |

### RAG - Query
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rag/retrieve` | Vector search |
| POST | `/rag/query` | RAG + generation |

### RAG - Collections
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rag/collections` | List collections |
| POST | `/rag/collections` | Create collection |
| GET | `/rag/collections/:id` | Get collection |
| PUT | `/rag/collections/:id` | Update collection |
| DELETE | `/rag/collections/:id` | Delete collection |
| POST | `/rag/collections/:id/move` | Move items |

### RAG - Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rag/settings` | Get settings |
| PUT | `/rag/settings` | Update settings |

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/set-sandbox` | Configure sandbox path |
| POST | `/api/agent/set-mode` | Set approval mode |
| GET | `/api/agent/status` | Get agent status |
| GET | `/api/agent/tools` | List available tools |
| POST | `/api/agent/execute` | Execute tool |
| POST | `/api/agent/approve/:id` | Approve pending call |
| POST | `/api/agent/reject/:id` | Reject pending call |
| GET | `/api/agent/pending` | List pending calls |

### MCP (Model Context Protocol)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mcp/servers` | List MCP servers |
| POST | `/api/mcp/servers` | Add MCP server |
| DELETE | `/api/mcp/servers/:id` | Remove MCP server |
| GET | `/api/mcp/tools` | List MCP tools |
| POST | `/api/mcp/tools/call` | Execute MCP tool |
| GET | `/api/mcp/tools/openai-format` | Get tools in OpenAI format |

### LLM Providers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/providers` | List providers |
| POST | `/api/providers/test` | Test provider |
| GET | `/api/providers/models` | List models |

### Usage Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/usage/stats` | Get usage statistics |
| GET | `/api/usage/daily` | Get daily breakdown |

---

## MCP Tools (Built-in)

11 tools available via `/api/mcp/tools`:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write to file |
| `list_dir` | List directory |
| `search_files` | Search by pattern |
| `run_command` | Execute shell command |
| `python_executor` | Run Python code |
| `web_search` | DuckDuckGo search |
| `screenshot` | Capture webpage |
| `database_query` | Read-only SQL |
| `think` | Record reasoning |
| `plan_task` | Create execution plan |

---

## RBAC

| Role | RAG | Agent | MCP | Admin |
|------|-----|-------|-----|-------|
| `user` | ❌ | ❌ | ❌ | ❌ |
| `rag_user` | ✅ | ❌ | ❌ | ❌ |
| `agent_user` | ✅ | ✅ | Built-in | ❌ |
| `admin` | ✅ | ✅ | ✅ All | ✅ |

---

## Related Docs- [CONTRACT.md](CONTRACT.md) - Core API protocol
- [RAG_CONTRACT.md](RAG_CONTRACT.md) - RAG pipeline
- [AGENT_CONTRACT.md](AGENT_CONTRACT.md) - Agent flow
