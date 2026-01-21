# Release Notes - v0.5.0-experimental

**Date**: 2026-01-22
**Status**: 🚧 **EXPERIMENTAL / ALPHA** 🚧

> [!WARNING]
> This release contains significant new features that have **NOT been battle-tested** in production environments.
> Use with caution. Known issues may exist in edge cases.

## New Features (Alpha)

### 📊 Comprehensive Dashboards
- **Overview**: Usage analytics with charts (RAG queries, LLM tokens).
- **Admin**: User management, guardrail violation logs, system stats.
- **User**: Personal collections, agent management, support tickets.
- **Backend**: New `admin` router and `support_tickets` / `guardrail_violations` tables.

### 🔌 Multi-Provider Embeddings
- **Providers**: OpenAI, Ollama, SentenceTransformers (HuggingFace).
- **Configuration**: Switch providers via `rag_settings`.
- **API**: New `/api/rag/embedding-models` endpoint.

## Known Limitations / Risks
1.  **Ticket System**: Basic CRUD only. No email notifications or SLA tracking yet.
2.  **Dashboard Performance**: Large datasets (>1M rows) may need pagination optimization in the UI.
3.  **Embedding Migration**: Changing embedding providers on existing data requires re-ingesting documents (no auto-migration yet).
4.  **UI Polish**: The dashboard UI is functional ("Developer Design") but lacks premium polish (planned for v0.6.0).

## Database Changes
- Added `usage_stats` table.
- Added `support_tickets` table.
- Added `guardrail_violations` table.
- **Action Required**: Run migration/init script or restart backend to apply schema changes.
