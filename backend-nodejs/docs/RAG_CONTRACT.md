# RAG Contract

**Version**: 1.0  
**Status**: Draft  
**Last Updated**: 2026-01-11

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
┌─────────────────────────────────────────────────────────────────────┐
│                         RAG QUERY PIPELINE                          │
│                                                                      │
│  Query → [Retrieval] → [Context Assembly] → [Grounding] → [Answering] │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Sub-Contract 1: Ingestion

**Purpose**: Process and index documents for retrieval

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `documents` | Document[] | Yes |
| `dataSourceId` | string | Yes |
| `chunkSize` | number | No (default 512) |
| `chunkOverlap` | number | No (default 50) |
| `embeddingModel` | string | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `jobId` | string | Ingestion job ID |
| `indexed` | number | Documents indexed |
| `chunks` | number | Total chunks created |
| `vectorIds` | string[] | IDs in vector store |
| `status` | enum | 'queued', 'processing', 'completed', 'failed' |

### Guarantees
- Documents chunked consistently
- Embeddings generated for all chunks
- Metadata preserved (source, page, etc.)
- User/org data isolated
- Job can be tracked asynchronously

### Failures
| Code | Meaning |
|------|---------|
| `PARSE_ERROR` | Cannot parse document format |
| `EMBEDDING_FAILED` | Embedding model error |
| `INDEX_FULL` | Storage quota exceeded |
| `UNSUPPORTED_FORMAT` | Document type not supported |
| `PERMISSION_DENIED` | User cannot ingest to this data source |

---

## Sub-Contract 2: Retrieval

**Purpose**: Find relevant documents for a query (includes reranking)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `dataSources` | string[] | No (all accessible) |
| `topK` | number | No (default 10) |
| `filters` | Filter[] | No |
| `rerank` | boolean | No (default true) |
| `rerankModel` | string | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `documents` | Document[] | Retrieved & reranked docs |
| `scores` | number[] | Relevance scores |
| `totalFound` | number | Total matches before topK |
| `dataSources` | string[] | Sources queried |

### Guarantees
- Results ordered by relevance (post-rerank if enabled)
- **Only queries data sources user has access to** (RBAC enforced)
- Maximum `topK` results returned
- Reranking improves precision over embedding similarity

### Failures
| Code | Meaning |
|------|---------|
| `NO_RESULTS` | No relevant documents found |
| `INDEX_UNAVAILABLE` | Vector database down |
| `EMBEDDING_FAILED` | Cannot embed query |
| `RERANK_FAILED` | Reranking service error |
| `NO_ACCESSIBLE_SOURCES` | User has no RAG access |

---

## Sub-Contract 3: Context Assembly

**Purpose**: Build LLM prompt with retrieved context

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `documents` | Document[] | Yes |
| `maxTokens` | number | Yes |
| `template` | string | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | Assembled prompt with context |
| `includedDocs` | number | Docs that fit in context |
| `tokenCount` | number | Total tokens used |
| `citations` | Citation[] | Source references |

### Guarantees
- Prompt fits within `maxTokens`
- Most relevant docs included first
- Citations mapped to source documents
- Clear separation of context and query

### Failures
| Code | Meaning |
|------|---------|
| `CONTEXT_OVERFLOW` | Cannot fit minimum required context |
| `TEMPLATE_ERROR` | Invalid prompt template |

---

## Sub-Contract 4: Grounding

**Purpose**: Verify retrieved context can support an answer (pre-generation check)

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `documents` | Document[] | Yes |
| `prompt` | string | Yes |
| `strictMode` | boolean | No (default false) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `isGroundable` | boolean | Query can be answered from sources |
| `groundingScore` | number | 0-1 confidence |
| `relevantDocs` | Document[] | Docs that support the query |
| `gaps` | string[] | Missing information |

### Guarantees
- Checks if query answerable from context
- Filters out irrelevant docs before generation
- Strict mode rejects if insufficient grounding

### Failures
| Code | Meaning |
|------|---------|
| `GROUNDING_FAILED` | Cannot verify (service error) |
| `INSUFFICIENT_CONTEXT` | Cannot answer from available docs (strict mode) |

---

## Sub-Contract 5: Answering

**Purpose**: Generate response using grounded context

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `prompt` | string | Yes |
| `groundedDocs` | Document[] | Yes |
| `citations` | Citation[] | Yes |
| `model` | string | No |
| `temperature` | number | No |
| `stream` | boolean | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Generated response |
| `citationsUsed` | Citation[] | Sources referenced in answer |
| `confidence` | number | Answer confidence 0-1 |

### Guarantees
- Answer based on grounded context only
- Citations included in response
- Streaming supported
- No hallucination (grounding already verified)

### Failures
| Code | Meaning |
|------|---------|
| `GENERATION_FAILED` | LLM error |
| `CONTEXT_IGNORED` | Answer doesn't use context (warning) |

---

## Data Source Access (RBAC)

RAG queries are filtered by user's data source access:

| Visibility | Who Can Query |
|------------|---------------|
| `public` | All org users |
| `role` | Users with specific roles |
| `team` | Users in specific teams |
| `private` | Only assigned users |
| `personal` | Only the owner |

See [RBAC_CONTRACT.md](RBAC_CONTRACT.md) for full access control details.

---

## API Endpoints

```
# Ingestion
POST   /api/rag/ingest              - Start ingestion job
GET    /api/rag/ingest/:jobId       - Get job status
DELETE /api/rag/ingest/:jobId       - Cancel job

# Data Sources
GET    /api/rag/sources             - List accessible sources
POST   /api/rag/sources             - Create data source
DELETE /api/rag/sources/:id         - Delete data source

# Query
POST   /api/rag/query               - Query with RAG
POST   /api/rag/retrieve            - Retrieve only (no generation)
```

---

## Failure Summary

| Code | Stage | Meaning |
|------|-------|---------|
| `PARSE_ERROR` | Ingestion | Cannot parse document |
| `EMBEDDING_FAILED` | Ingestion/Retrieval | Embedding model error |
| `NO_RESULTS` | Retrieval | No relevant docs found |
| `INDEX_UNAVAILABLE` | Retrieval | Vector DB down |
| `CONTEXT_OVERFLOW` | Context Assembly | Cannot fit context |
| `GENERATION_FAILED` | Answering | LLM error |
| `NOT_GROUNDED` | Grounding | Answer not supported |
| `PERMISSION_DENIED` | Any | User lacks access |

---

## Contract Compliance Checklist

- [ ] Ingestion contract implemented
- [ ] Retrieval contract implemented (with reranking)
- [ ] Context assembly contract implemented
- [ ] Grounding contract implemented
- [ ] Answering contract implemented
- [ ] Data source RBAC enforced
- [ ] API endpoints implemented
