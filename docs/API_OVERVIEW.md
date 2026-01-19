# BeyondCloud API Overview

This document provides a high-level map of the BeyondCloud service architecture, ports, and base URLs.

## 📡 Backend Architecture

| Service | Responsibility | Port | Base URL |
|---------|----------------|------|----------|
| **Node.js Backend** | Auth, Conversations, Settings | 3000 | `/api` |
| **Python Backend** | RAG, Agents, MCP, Analytics | 8001 | `/api` |

> **Note**: The Python backend hosts all AI-related services in a single FastAPI application.

---

## Python Backend Routes (/api)

### Core
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/models` | GET | List available models |

### RAG (Knowledge Base)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rag/sources` | GET | List sources |
| `/rag/ingest` | POST | Ingest text |
| `/rag/ingest/file` | POST | Ingest file |
| `/rag/retrieve` | POST | Vector search |
| `/rag/query` | POST | RAG + generation |
| `/rag/sources/:id` | DELETE | Delete source |
| `/rag/sources/:id/visibility` | PUT | Update visibility |
| `/rag/settings` | GET/PUT | RAG settings |
| `/rag/collections` | GET/POST | Manage collections |

### Agent
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agent/set-sandbox` | POST | Configure sandbox |
| `/agent/set-mode` | POST | Set agent mode |
| `/agent/execute` | POST | Execute tool |
| `/agent/approve/:id` | POST | Approve action |
| `/agent/status` | GET | Get agent status |

### MCP (Model Context Protocol)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp/servers` | GET/POST/DELETE | Manage MCP servers |
| `/mcp/tools` | GET | List available tools |
| `/mcp/tools/call` | POST | Execute MCP tool |

### Usage Analytics
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/usage/analytics` | GET | Get usage stats |

---

## 🔗 Contract Documents

| Document | Contents |
|----------|----------|
| [CONTRACT.md](CONTRACT.md) | Core API protocol, auth, errors |
| [AGENT_CONTRACT.md](AGENT_CONTRACT.md) | Agent tool execution flow |
| [RAG_CONTRACT.md](RAG_CONTRACT.md) | RAG pipeline contracts |
| [RBAC_CONTRACT.md](RBAC_CONTRACT.md) | Access control matrix |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | ER diagram and tables |

---

## ⚠️ Cross-Service Guarantees

1. **User Isolation**: No user can access another user's data
2. **Atomic Operations**: All database changes are transactional
3. **Approval Flow**: Dangerous agent actions require user approval
