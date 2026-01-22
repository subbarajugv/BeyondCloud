# BeyondCloud Project Summary

A multi-user LLM interface with dual backends, RAG capabilities, and agentic tools.

## 📁 Directory Structure

```
llamacpp-auth-webui/
├── backend-nodejs/       # Auth, Conversations, Settings
├── backend-python/       # RAG, Agents, MCP, LLM Gateway, Analytics
├── frontend/             # Svelte 5 WebUI
└── docs/                 # API Contracts & Documentation
```

## 🚀 Current Status

| Component | Status | Port |
|-----------|--------|------|
| **Node.js Backend** | ✅ Active | 3000 |
| **Python Backend** | ✅ Active | 8008 |
| **Frontend** | ✅ Active | 5173 (dev) |

## ✅ Implemented Features

- **Authentication**: JWT + refresh tokens + RBAC
- **Conversations**: Full CRUD with branching support
- **RAG System**: Ingest, retrieve, query with pgvector
- **Collections**: Hierarchical folder organization for RAG sources
- **Storage**: Local (dev) or S3-compatible (prod)
- **Agent Tools**: Sandbox execution with approval flow
- **MCP Integration**: External tool servers
- **Usage Analytics**: LLM/RAG/Agent metrics tracking
- **RAG Settings UI**: Configurable chunking, reranking, context assembly
- **Unified LLM Gateway**: Centralized LLM routing with streaming support
- **Resilient APIs**: Retry logic with exponential backoff, connection pooling

## 📚 Key Documentation

| Document | Contents |
|----------|----------|
| [API Overview](docs/API_OVERVIEW.md) | All routes and endpoints |
| [Core Contract](docs/CONTRACT.md) | Protocol and error formats |
| [RAG Contract](docs/RAG_CONTRACT.md) | Ingestion and retrieval |
| [Database Schema](docs/DATABASE_SCHEMA.md) | ER diagram |
| [RBAC Contract](docs/RBAC_CONTRACT.md) | Access control |

---

**Last Updated:** 2026-01-23  
**Status:** 🚀 Active Development
