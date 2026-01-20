# BeyondCloud: Enterprise AI Agent Platform

## Executive Summary
**BeyondCloud: The Universal AI Operating System for Enterprise.**

BeyondCloud is a secure, modular platform that lets you **Bring Your Own Model (BYO-LLM)** and infrastructure. It bridges the gap between local privacy (Ollama, air-gapped) and cloud power (OpenAI, Anthropic), offering a unified "Operating System" for RAG and Agents.

### Heritage
> Originally forked from the community-favorite `llama.cpp webui`, minimal-chat has been *significantly refactored* into an enterprise-grade platform. We retained the speed and simplicity of the original while adding the security, modularity, and agentic capabilities required for business.

## Key Value Proposition

### 1. **Dual-Mode Agent Architecture** 🧠
Unique flexibility to run agents where it makes sense:
- **Local Mode**: Zero-latency, air-gapped execution on developer machines. Direct FastMCP integration.
- **Remote Mode**: Centralized, RBAC-protected execution on servers. HTTP/SSE transport.

### 2. **Enterprise-Grade Security** 🛡️
- **RBAC (Role-Based Access Control)**: Granular permissions (Admin, Agent User, Viewer).
- **Guardrails**: Automated safety checks for dangerous tools (`run_command` blocked by safety level).
- **Audit Logs**: Full traceability of every tool call, thought, and action.

### 3. **FastMCP Integration** 🚀
- **Stdio/HTTP/Direct Support**: Seamlessly switch between transport layers.
- **11+ Built-in Tools**: File ops, Web Search, Database Query (Read-only safe), Python Sandbox.
- **Extensible**: Add new tools in <10 lines of Python.

### 4. **Modern Tech Stack** 🛠️
- **Backend**: Python (FastAPI) + FastMCP
- **Frontend**: Svelte 5 + TailwindCSS + DaisyUI
- **LLM Support**: Ollama, llama.cpp, OpenAI-compatible APIs

### 5. Multi-Tenant & Multi-Cloud Freedom 🏢☁️
- **User & Data Isolation**: Built-in RBAC and Row-Level Security (RLS) ensure complete tenant isolation.
### 5. Multi-Tenant & Multi-Provider Freedom 🏢☁️
- **BYO-LLM (Bring Your Own Model)**: Each tenant can configure their preferred provider:
    - **Tenant A**: Runs entirely on local **Ollama/llama.cpp** for privacy.
    - **Tenant B**: Uses **OpenAI/Groq** for speed and performance.
- **Tenant Isolation**: RBAC and RLS ensure that Tenant A's data never touches Tenant B's infrastructure.
- **Infrastructure Independent**: Deploy on-premise, AWS, or Azure without code changes.

## Capabilities

### 1. Autonomous Agents 🤖
- **ReAct Loop**: Plan → Think → Execute → Observe. Self-correcting with error recovery.
- **Dual-Mode Execution**: Run locally (zero-latency) or remotely (centralized, RBAC-protected).
- **Human-in-the-Loop**: Configurable approval gates for dangerous actions.

### 2. Enterprise-Grade RAG 📚
Not a toy. This is a **production-grade retrieval engine**:

| Layer | Feature | Details |
| :--- | :--- | :--- |
| **Ingestion** | Multi-Format | PDF, Markdown, DOCX, Code Files |
| | Smart Chunking | Sentence, Paragraph, Semantic, and Recursive strategies |
| | S3-Compatible | Store originals in any S3-compatible bucket (AWS, Minio, etc.) |
| **Storage** | pgvector | Native Postgres vector search |
| | Hierarchical Collections | Nested folders with RBAC (public, role, team, private, personal) |
| **Query Enhancement** | Spelling Correction | Auto-fixes typos before retrieval |
| | LLM Rewriting | Rewrites vague queries for better retrieval |
| | Query Expansion | Adds synonyms: `auth errors` → `authentication failures` |
| | Query Decomposition | Breaks multi-hop questions into sub-queries |
| | Intent Detection | Classifies query type (factual, procedural, troubleshooting) |
| **Retrieval** | HyDE | Hypothetical Document Embeddings for improved recall |
| | Hybrid Search | **BM25 Keyword + Vector Semantic** combined via **Reciprocal Rank Fusion (RRF)** |
| | Cross-Encoder Reranking | Scores query-document pairs for precision |
| **Synthesis** | Grounding Score | Calculates how well responses are supported by sources |
| | Citation Enforcement | Optionally require citations to prevent hallucinations |

### 3. Defense-in-Depth Guardrails 🛡️
**Agent Guardrails** (for Tools):
- Command Blocklist: `sudo`, `rm -rf`, fork bombs, etc.
- Path Restrictions: Cannot access `/etc`, `/root`, `~/.ssh`.
- Sandbox Enforcement: File operations locked to declared workspace.

**RAG Guardrails** (for Queries):
- Prompt Injection Detection: Catches `ignore previous instructions` attacks.
- Toxicity Filtering: Blocks harmful queries.
- PII Detection: Warns on sensitive data in queries.

### 4. Usage Analytics & Metering 📊
Built-in counters for:
- `rag_queries`, `rag_ingestions`, `rag_chunks_retrieved`
- `agent_tool_calls`, `agent_approvals`, `agent_rejections`
- `llm_requests`, `llm_tokens_input`, `llm_tokens_output`
- Daily/weekly/monthly breakdowns per user (ready for billing).

### 5. Sandboxed Execution 🏗️
- Safe file and code operations in isolated environments.
- Configurable sandbox path per user/session.

### 6. Real-time Streaming ⚡
- SSE-based live updates of agent thoughts, tool calls, and results.

## Use Cases
- **DevOps Automation**: "Check git status and deploy to staging" (with approval).
- **Data Analysis**: "Query the database and visualize sales trends."
- **Code Refactoring**: "Read this file and refactor the class structure."
- **Knowledge Management**: "Search internal docs and answer compliance questions."
- **Secure Copilot**: Deploy inside your firewall, no data leaves.

## Ready for Business
- **Docker Ready**: One-command deployment.
- **Observability**: OpenTelemetry tracing integration (Jaeger/Prometheus ready).
- **Scalable**: Stateless backend design.
- **Usage Tracking**: Built-in metering for billing integration.

