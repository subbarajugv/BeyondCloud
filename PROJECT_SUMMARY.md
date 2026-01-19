# BeyondCloud Project Summary

A multi-user LLM interface with dual backends, RAG capabilities, and agentic tools.

## 📁 Directory Structure

```
llamacpp-auth-webui/
├── backend-nodejs/       # Auth, Conversations, and Global Settings
├── backend-python/       # RAG System, Agent Logic, and Analytics
├── frontend/             # Svelte 5 WebUI with authenticated routes
├── docs/                 # Documentation & API Contracts
├── agent-daemon/         # Background agent processes
└── public/               # Static assets
```

## 🚀 Current Status

| Component | Status | Technology |
|-----------|--------|------------|
| **Core Auth** | ✅ Done | Node.js + Express + JWT |
| **Conversations** | ✅ Done | Node.js + PostgreSQL |
| **RAG Ingestion** | ✅ Done | Python + FastAPI + pgvector |
| **Vector Search** | ✅ Done | Python + FastAPI |
| **Agent Tools** | 🚧 Beta | Python + MCP |
| **Analytics** | ✅ Done | Python + OpenTelemetry |

## 📚 Key Documentation

1. **[API Overview](docs/API_OVERVIEW.md)**: Service mapping and ports (3000, 8000, 8001).
2. **[Core Contract](docs/CONTRACT.md)**: Protocol standards and error formats.
3. **[RAG Logic](docs/RAG_CONTRACT.md)**: Ingestion and retrieval specifications.
4. **[Database Schema](docs/DATABASE_SCHEMA.md)**: ER Diagram and security analysis.
5. **[Implementation Phases](docs/PHASES.md)**: Roadmap and completion status.

## ✨ Features

- **Authentication**: JWT-based auth with refresh token rotation and RBAC.
- **RAG System**: Ingest documents (PDF, Text) and query them with semantic search.
- **Agentic Chat**: Support for tool calling and Model Context Protocol (MCP).
- **Dual Backend**: Optimized performance with Node.js for I/O and Python for AI logic.
- **Multi-User**: Strict data isolation and role-based access control.

---

**Last Updated:** 2026-01-19  
**Status:** 🚀 Active Development (Phase 4/5)
