# BeyondCloud: Enterprise Premium Product Roadmap

This document outlines the strategic initiatives required to transform BeyondCloud into a market-leading enterprise AI platform.

## 🎨 1. Magic UX (Sensory & Adaptive Interface)
*   [ ] **Multimodal Reasoning**
    *   Enable vision-capable models (`minicpm-v`, `llama3-vision`)
    *   Direct image/PDF analysis with OCR fallback
*   [ ] **Dynamic Data Visualization**
    *   Auto-render charts (Recharts/Chart.js) from Python agent output
    *   Interactive data tables for CSV/JSON responses
*   [ ] **Voice-First Experience**
    *   Streaming Speech-to-Text (STT) for prompt input
    *   Low-latency Text-to-Speech (TTS) for agent personality

## 🧠 2. Deep Intelligence (Context & Memory)
*   [ ] **Knowledge Graph Integration (GraphRAG)**
    *   Extract entities and relationships from ingested docs
    *   Enable relational queries beyond simple vector similarity
*   [ ] **Long-term User Memory**
    *   Persistent user profile (preferences, coding style, tech stack)
    *   Cross-session context recall
*   [ ] **Inline Semantic Citations**
    *   Source highlighting: click an answer sentence to see the source segment
    *   Hover-cards for document metadata

## 🤖 3. Agent Autonomy (Power Workflows)
*   [ ] **Multi-Agent Orchestration**
    *   Implement "Agent Teams" (Researcher, Coder, Reviewer)
    *   Asynchronous background task execution
*   [ ] **Native Business Connectors**
    *   GitHub/GitLab integration for direct code commits
    *   Google/Office 365 connectors for scheduling and email
*   [ ] **Advanced Action Panel**
    *   Sidebar to view/edit agent plans before execution
    *   Detailed execution logs and "Step-Back" debugging

## 📚 4. Advanced RAG Pipeline
*   [ ] **RAG Settings UI**
    *   Embedding model selector (MiniLM, MPNet, BGE)
    *   Reranker model selector
    *   Hybrid search toggle + BM25 weight slider
    *   Reranking toggle + top-k setting
*   [ ] **Context Assembly Options**
    *   Ordering: Score descending, chronological, source-grouped
    *   Max context token limit
    *   Context compression (summarize long chunks)
*   [ ] **LLM Reranking**
    *   Send top-N candidates to LLM for relevance scoring
    *   Re-sort by LLM confidence
*   [ ] **Guardrails**
    *   Pre-query validation (PII detection, toxicity, blocklist)
    *   Post-generation validation (hallucination check, citation required)
    *   Admin dashboard for guardrail violations

## 🔐 5. GDPR & Data Compliance
*   [x] **Right to Erasure (Delete All)** ✅
    *   `DELETE /api/admin/users/:id/data` - Admin deletes user data
    *   `DELETE /api/admin/my-data?confirm=true` - Self-service deletion
    *   Purges: sources, chunks, collections, usage stats, tickets, traces
*   [x] **Right to Portability (Export)** ✅
    *   `GET /api/admin/users/:id/export` - Admin exports user data
    *   `GET /api/admin/my-data/export` - Self-service export
    *   Exports as ZIP with JSON files
*   [ ] **Data Retention Policies**
    *   Configurable auto-delete after N days
    *   Admin UI for retention settings
*   [ ] **Storage Cleanup** (Future)
    *   Clean S3/local storage files on deletion
    *   Clear FAISS/BM25 indices


## 📊 6. Extensible Dashboards & Observability

### Core Dashboards (Built-in)
*   [ ] **Admin Dashboard**
    *   User management (CRUD, roles, quotas)
    *   Guardrail violation logs
    *   Document/collection management
*   [ ] **Usage Analytics Dashboard**
    *   RAG queries, agent tool calls, LLM requests
    *   Token usage, embedding costs
    *   Daily/weekly/monthly breakdowns
*   [ ] **User Dashboard**
    *   My Usage, My Collections, My Agents
    *   Settings, Support (raise/track tickets)

### Custom Dashboard Architecture (Extensibility)
*   [ ] **Widget-Based System**
    *   Dashboard = array of draggable widgets (react-grid-layout)
    *   Persist layout per user/tenant
    *   Built-in widgets: `usage-counter`, `line-chart`, `bar-chart`, `table`
*   [ ] **Widget Registry**
    *   Register custom widgets via plugin API
    *   Each widget defines: `dataSource`, `config`, `render()`
*   [ ] **Query Builder** (Power Users)
    *   Define custom metrics via SQL or API queries
    *   Parameterized queries: `:user_id`, `:date_range`
    *   Save and share queries
*   [ ] **Dashboard API**
    *   `GET/POST/PUT /api/dashboards` - CRUD for dashboard configs
    *   `GET /api/dashboards/:id/data` - Fetch all widget data
    *   `POST /api/dashboards/:id/share` - Share with team/roles

### Premium Features
*   [ ] **Scheduled Reports**
    *   Email dashboard PDF weekly/monthly
*   [ ] **Embedding**
    *   `<iframe>` embed with signed URLs for external portals
*   [ ] **Audit Trail UI**
    *   Admin view of all traces, filter by user/operation/time



## 🎫 7. Internal Issue Tracker (Dog-fooding)
*   [ ] **Native Issue Management**
    *   Extend ticket system for development issue tracking
    *   Support: bugs, features, optimizations, docs
    *   Labels, milestones, priority levels
*   [ ] **Git Integration**
    *   Link commits and PRs to issues
    *   Release notes auto-linking (`BC-###` format)
*   [ ] **AI-Powered Issue Management**
    *   MCP server for AI agents to query/create issues
    *   Auto-categorization and priority suggestions

> 📄 **Detailed Design**: [FUTURE_ISSUE_TRACKER.md](FUTURE_ISSUE_TRACKER.md)

## 🛡️ 8. Enterprise Hardening (Governance)
*   [ ] **Intelligent Model Routing**
    *   Cost/Speed optimization: Route small tasks to 1B models, logic to 32B+ models
    *   Local vs. Cloud routing based on data sensitivity
*   [ ] **Full Knowledge Library UI**
    *   Admin dashboard for document management
    *   Semantic maps visualizing the knowledge base
*   [ ] **Active Hallucination Detection**
    *   Automated "Reflexion" step to check answers against sources
    *   Confidence scoring for all RAG responses

