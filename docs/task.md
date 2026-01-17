# WebUI Authentication Integration Analysis

## Tasks
- [x] Analyze WebUI architecture
  - [x] Explore main routes and layout
  - [x] Examine store structure (chat, settings, server)
  - [x] Review component hierarchy
  - [x] Understand API integration (chat service, database)
- [x] Create implementation plan
  - [x] Document architecture findings
  - [x] Design authentication flow
  - [x] Plan backend modifications
  - [x] Plan frontend modifications
  - [x] Define verification approach
- [x] Enhance authentication security
  - [x] Add forgot/reset password endpoints
  - [x] Add email verification flow
  - [x] Add session management
  - [x] Create secure token schema
  - [x] Define rate limiting policies
  - [x] Document secure password reset flow
  - [x] Document secure logout flow
- [x] Add multi-backend support plan
  - [x] Assess difficulty and necessity
  - [x] Document OpenAI-compatible providers
  - [x] Create Phase 0 for multi-backend integration
  - [x] Add provider configuration code examples
- [x] Create component-based architecture
  - [x] Define independent components (frontend, backend)
  - [x] Create API contract for parallel development
  - [x] Add MCP integration as Phase 6 (placeholder)
  - [x] Document placeholder pattern

## Progress Summary

### ✅ Phase 1: Backend Gaps (Complete)
- **Auth Endpoints**: Added `/api/auth/refresh`, `/api/auth/forgot-password`, `/api/auth/reset-password`.
- **Chat Proxy**: Added `/api/chat/completions` with streaming support.
- **Database**: Added `refresh_tokens` and `password_reset_tokens` tables.
- **Frontend**: Fixed routing from hash-based (`#/chat`) to path-based (`/chat`).

### ✅ Phase 4: RAG & Tracing (Complete)
- **Python AI Service**: FastAPI microservice setup.
- **Observability**: Custom OTel-compatible tracing system logging to PostgreSQL.
- **RAG Engine**: 
  - `pgvector` integration for persistent embeddings.
  - `FAISS` service for fast in-memory search.
  - Ingestion pipeline for `.txt`, `.md`, `.pdf`, `.docx`, `.html`
  - **Hybrid Search**: BM25 + vector with Reciprocal Rank Fusion
  - **Reranking**: Cross-encoder (ms-marco-MiniLM) for precision
  - **Answer Service**: LLM generation with context assembly + citations
- **Query Service**:
  - Spelling correction (pyspellchecker)
  - LLM-based query rewriting
  - Human-in-the-loop confirmation
- **Environment**: Managed via `uv` in `.venv`.


## Phase Order (Updated)

| Phase | Component | Status |
|-------|-----------|--------|
| 0 | Multi-Backend LLM Integration | ✅ Done |
| 1 | Backend (Auth, DB, APIs) | ✅ Done |
| 2 | Frontend (Auth UI) | ✅ Done |
| 3 | Data Migration | ✅ Done (Hybrid) |
| 4 | RAG & Tracing (Basic) | ✅ Done |
| 5 | Agents & Tools | ✅ Done (Core) |
| **6** | **MCP Integration** | 🚧 Next |
| 7 | RAG Advanced (UI Options) | To Do |
| 8 | Security & Production | To Do |

### Phase 6: MCP Integration
- External tool server connections
- Tool discovery and execution
- Frontend server management UI

### Phase 7: RAG Advanced (User Options)
- **Chunking Options**: chunk size, overlap, sentence boundary, semantic chunking
- **Reranking Options**: model selection, score threshold, result ordering
- **Context Assembly**: token limits, ordering strategies, overlap handling
- **Grounding Rules**: citation requirements, hallucination detection
- **RAG System Message**: custom prompts, persona, guardrails

### Phase 8 Planned (Security)
- **RBAC**: Role-based access control (user, rag_user, agent_user, admin, owner)
- Rate limiting, API key management
- Production hardening

## Documentation
- [implementation_plan.md](./implementation_plan.md) - AI Service & RAG Architecture
- [REMOVING_DEXIE.md](./REMOVING_DEXIE.md) - Optional IndexedDB removal guide
- [api-contract.md](./api-contract.md) - API specification

