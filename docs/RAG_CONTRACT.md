# RAG Contract (BeyondCloud)

**Version**: 2.0  
**Status**: Active  
**Last Updated**: 2026-01-19

Retrieval-Augmented Generation - ground LLM responses in retrieved documents.

> **Note**: RAG is independent of the Agent system and can be used standalone.

---

## RAG Architecture

```
                    ┌─────────────────────────────────────┐
                    │           INGESTION PIPELINE         │
                    │  Documents → Chunking → Embedding    │
                    │              → Vector DB             │
                    └─────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RAG QUERY PIPELINE                               │
│                                                                             │
│  Query → [Pre-Query Guard] → [Retrieval] → [Context Assembly]              │
│              → [Grounding] → [Answering] → [Post-Gen Guard] → Response     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sub-Contract 1: Ingestion ✅

**Purpose**: Process and index documents for retrieval  
**Status**: Implemented

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `documents` | Document[] | Yes |
| `dataSourceId` | string | Yes |
| `chunkSize` | number | No (default 512) |
| `chunkOverlap` | number | No (default 50) |
| `visibility` | string | No (default "private") |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `source_id` | string | Created source ID |
| `chunk_count` | number | Total chunks created |
| `status` | enum | 'completed', 'failed' |

### Guarantees
- Documents chunked consistently
- Embeddings generated for all chunks
- Metadata preserved (source, page, etc.)
- User/org data isolated via `visibility` field

### Failures
| Code | Meaning |
|------|---------|
| `PARSE_ERROR` | Cannot parse document format |
| `EMBEDDING_FAILED` | Embedding model error |
| `UNSUPPORTED_FORMAT` | Document type not supported |

---

## Sub-Contract 2: Pre-Query Validation 🚧

**Purpose**: Validate and filter user queries before retrieval  
**Status**: Planned (Phase B)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `user_id` | string | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `passed` | boolean | Query passed all checks |
| `blocked_reason` | string | If failed, the reason |
| `sanitized_query` | string | Cleaned query text |

### Checks
| Check Type | Description |
|------------|-------------|
| `blocklist` | Reject queries containing blocked terms |
| `pii_detection` | Flag queries containing PII |
| `toxicity` | Block toxic or harmful queries |
| `intent_classification` | Classify query intent for routing |

### Guarantees
- All queries logged for audit
- Blocked queries do not reach LLM
- Configurable per-organization

### Failures
| Code | Meaning |
|------|---------|
| `QUERY_BLOCKED` | Query violated content policy |
| `PII_DETECTED` | Query contains personal information |

---

## Sub-Contract 3: Retrieval ✅

**Purpose**: Find relevant documents for a query (includes reranking)  
**Status**: Implemented

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `source_ids` | string[] | No (all accessible) |
| `top_k` | number | No (default 5) |
| `min_score` | float | No (default 0.5) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `chunks` | Chunk[] | Retrieved & ranked chunks |
| `scores` | number[] | Relevance scores |

### Guarantees
- Results ordered by relevance
- **Only queries sources user has access to** (RBAC enforced)
- Supports both private and shared sources

### Failures
| Code | Meaning |
|------|---------|
| `NO_RESULTS` | No relevant documents found |
| `EMBEDDING_FAILED` | Cannot embed query |

---

## Sub-Contract 4: Context Assembly ⚠️

**Purpose**: Build LLM prompt with retrieved context  
**Status**: Partially Implemented (system_message pending)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `chunks` | Chunk[] | Yes |
| `system_message` | string | No |
| `grounding_rules` | GroundingRules | No |
| `max_tokens` | number | Yes |

### GroundingRules Schema
```json
{
  "min_sources": 2,
  "citation_style": "inline",
  "require_exact_match": false,
  "fallback_message": "I don't have enough information."
}
```

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | Assembled prompt with context |
| `citations` | Citation[] | Source references |
| `token_count` | number | Total tokens used |

### Guarantees
- System message prepended to prompt
- Most relevant chunks included first
- Citations mapped to source documents

### Failures
| Code | Meaning |
|------|---------|
| `CONTEXT_OVERFLOW` | Cannot fit minimum required context |

---

## Sub-Contract 5: Grounding ⚠️

**Purpose**: Verify retrieved context can support an answer  
**Status**: Partially Implemented (rules pending)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `chunks` | Chunk[] | Yes |
| `grounding_rules` | GroundingRules | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `is_groundable` | boolean | Query answerable from sources |
| `grounding_score` | number | 0-1 confidence |
| `gaps` | string[] | Missing information |

### Guarantees
- Enforces `min_sources` from grounding rules
- Returns fallback message if insufficient grounding

### Failures
| Code | Meaning |
|------|---------|
| `INSUFFICIENT_CONTEXT` | Cannot answer from available docs |

---

## Sub-Contract 6: Answering ✅

**Purpose**: Generate response using grounded context  
**Status**: Implemented

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `prompt` | string | Yes |
| `model` | string | No |
| `generate` | boolean | No (default true) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Generated response |
| `citations` | Citation[] | Sources used |

### Guarantees
- Answer based on grounded context
- Citations included in response

### Failures
| Code | Meaning |
|------|---------|
| `GENERATION_FAILED` | LLM error |

---

## Sub-Contract 7: Post-Generation Validation 🚧

**Purpose**: Validate LLM output before delivery  
**Status**: Planned (Phase B)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `response` | string | Yes |
| `sources` | Chunk[] | Yes |
| `query` | string | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `passed` | boolean | Response passed all checks |
| `issues` | Issue[] | List of detected issues |
| `flagged` | boolean | Requires admin review |

### Checks
| Check Type | Description |
|------------|-------------|
| `toxicity` | Block toxic or harmful responses |
| `hallucination` | Verify claims are grounded in sources |
| `policy_compliance` | Check against org content policy |

### Guarantees
- All responses logged for audit
- Failed responses flagged for admin review
- Admins notified of policy violations

### Failures
| Code | Meaning |
|------|---------|
| `RESPONSE_BLOCKED` | Response violated content policy |
| `HALLUCINATION_DETECTED` | Response not grounded in sources |

---

## Sub-Contract 8: Audit & Notification 🚧

**Purpose**: Log all RAG interactions and notify on violations  
**Status**: Planned (Phase C)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `event_type` | string | Yes |
| `user_id` | string | Yes |
| `details` | object | Yes |
| `flagged` | boolean | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `log_id` | string | Audit log entry ID |
| `notifications_sent` | number | Admin notifications sent |

### Guarantees
- All RAG queries stored in `guardrail_logs`
- Flagged content triggers admin notification
- Supports email and webhook channels

---

## Data Source Access (RBAC) ✅

**Status**: Implemented

| Visibility | Who Can Query |
|------------|---------------|
| `private` | Only the owner |
| `shared` | All authenticated users |

See [RBAC_CONTRACT.md](RBAC_CONTRACT.md) for full access control details.

---

## API Endpoints

```
# Ingestion
POST   /rag/ingest              - Ingest text content
POST   /rag/ingest/file         - Upload and ingest file
GET    /rag/sources             - List accessible sources
DELETE /rag/sources/:id         - Delete data source

# Query
POST   /rag/retrieve            - Vector search only
POST   /rag/query               - Full RAG with generation

# Configuration (Admin)
PUT    /rag/sources/:id/visibility  - Update source visibility
PUT    /rag/sources/:id/config      - Update system_message & grounding_rules (Planned)
```

---

## Contract Compliance Checklist

### Core Pipeline
- [x] Ingestion contract implemented
- [x] Retrieval contract implemented
- [x] Context assembly contract implemented
- [x] Answering contract implemented
- [x] Data source RBAC enforced (visibility)

### Guardrails (Planned)
- [ ] Pre-query validation implemented
- [ ] Post-generation validation implemented
- [ ] Grounding rules enforcement
- [ ] System message injection

### Admin & Audit (Planned)
- [ ] Guardrail logging to database
- [ ] Admin notification on violations
- [ ] Admin panel for review
