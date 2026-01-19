# BeyondCloud API Overview

This document provides a high-level map of the BeyondCloud service architecture, ports, and base URLs. For detailed data schemas and protocol guarantees, refer to the specific contract files.

## 📡 Backend Architecture

| Service | Responsibility | Port | Base URL | Detailed Contract |
|---------|----------------|------|----------|-------------------|
| **Core (Node.js)** | Auth, Conversations, Settings | 3000 | `/api` | [CONTRACT.md](CONTRACT.md) |
| **Agent Engine (Python)** | Agents, MCP, Sandbox | 8000 | `/api` | [AGENT_CONTRACT.md](AGENT_CONTRACT.md) |
| **RAG Engine (Python)** | Vector Search, Ingestion | 8001 | `/rag` | [RAG_CONTRACT.md](RAG_CONTRACT.md) |
| **Analytics (Python)** | Usage Metrics, Tracing | 8000 | `/usage` | [CONTRACT.md](CONTRACT.md) |

---

## 🚦 Protocol Standards

BeyondCloud adheres to a strict protocol standard for all services:

- **Auth**: All protected endpoints require a Bearer JWT in the `Authorization` header.
- **Format**: All requests and responses are JSON (except SSE streams).
- **Errors**: All services return a standardized error format (see [CONTRACT.md](CONTRACT.md#4-failures)).

---

## 🔗 Deep Links to Specifications

### [Core API (Node.js)](CONTRACT.md)
- User Authentication (Login, Register, Logout)
- Conversation & Message Management
- Global Settings

### [Agent System (Python)](AGENT_CONTRACT.md)
- Intent Parsing
- Tool Execution & Approval Flow
- MCP (Model Context Protocol) Integration

### [Knowledge Base / RAG (Python)](RAG_CONTRACT.md)
- Document Ingestion (Files/Text)
- Prompt Grounding & Citations
- Vector Search

### [Access Control (RBAC)](RBAC_CONTRACT.md)
- Role Definitions (`admin`, `user`, `agent_developer`)
- Permission Matrix for all resources

---

## ⚠️ Cross-Service Guarantees

1. **User Isolation**: No user can access another user's conversations or private RAG sources.
2. **Atomic Ingestion**: Document ingestion either completes fully (with embeddings) or fails cleanly.
3. **Approval Flow**: Dangerous agent actions (file writes, code execution) MUST be approved by the user via the defined protocol.
