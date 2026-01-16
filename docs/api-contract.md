# API Contract Specification

## Overview

This document defines the complete API contract between frontend and backend. Once agreed upon, both teams can develop independently.

**Base URL**: `/api`  
**Content-Type**: `application/json`  
**Authentication**: Bearer token in `Authorization` header

---

## Authentication Endpoints

### POST /auth/register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (201):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "emailVerified": false,
    "createdAt": "2025-01-11T10:00:00Z"
  },
  "message": "Verification email sent"
}
```

**Errors:** `400` (validation), `409` (email exists)

---

### POST /auth/login

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "rememberMe": false
}
```

**Response (200):**
```json
{
  "accessToken": "eyJhbG...",
  "refreshToken": "eyJhbG...",
  "expiresIn": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "emailVerified": true
  }
}
```

**Errors:** `401` (invalid credentials), `403` (account locked), `423` (email not verified)

---

### POST /auth/logout

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

---

### POST /auth/refresh

**Request:**
```json
{
  "refreshToken": "eyJhbG..."
}
```

**Response (200):**
```json
{
  "accessToken": "eyJhbG...",
  "expiresIn": 900
}
```

---

### POST /auth/forgot-password

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "If email exists, reset link sent"
}
```

---

### POST /auth/reset-password

**Request:**
```json
{
  "token": "reset-token-from-email",
  "password": "newSecurePassword123"
}
```

**Response (200):**
```json
{
  "message": "Password reset successfully"
}
```

---

### GET /auth/me

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "emailVerified": true,
  "createdAt": "2025-01-11T10:00:00Z",
  "lastLoginAt": "2025-01-11T15:00:00Z"
}
```

---

## Conversations Endpoints

### GET /conversations

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "conversations": [
    {
      "id": "uuid",
      "name": "Chat about AI",
      "createdAt": "2025-01-11T10:00:00Z",
      "lastModified": "2025-01-11T15:00:00Z",
      "messageCount": 12
    }
  ]
}
```

---

### POST /conversations

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "name": "New Conversation"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "New Conversation",
  "createdAt": "2025-01-11T10:00:00Z"
}
```

---

### GET /conversations/:id

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Chat about AI",
  "createdAt": "2025-01-11T10:00:00Z",
  "lastModified": "2025-01-11T15:00:00Z"
}
```

---

### PUT /conversations/:id

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "name": "Updated Name"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Updated Name",
  "lastModified": "2025-01-11T16:00:00Z"
}
```

---

### DELETE /conversations/:id

**Headers:** `Authorization: Bearer <accessToken>`

**Response (204):** No content

---

## Messages Endpoints

### GET /messages/:convId

**Headers:** `Authorization: Bearer <accessToken>`

**Query Params:** `?limit=50&before=messageId`

**Response (200):**
```json
{
  "messages": [
    {
      "id": "uuid",
      "convId": "uuid",
      "parentId": null,
      "role": "user",
      "content": "Hello!",
      "type": "text",
      "model": null,
      "timestamp": 1704978000000,
      "extra": null
    },
    {
      "id": "uuid",
      "convId": "uuid",
      "parentId": "previous-msg-id",
      "role": "assistant",
      "content": "Hi there! How can I help?",
      "type": "text",
      "model": "gpt-4o",
      "timestamp": 1704978001000,
      "extra": null
    }
  ]
}
```

---

### POST /messages

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "convId": "uuid",
  "parentId": "uuid or null",
  "role": "user",
  "content": "Hello!",
  "type": "text",
  "extra": null
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "convId": "uuid",
  "timestamp": 1704978000000
}
```

---

## Chat Completion Endpoint

### POST /chat/completions

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"}
  ],
  "model": "gpt-4o",
  "provider": "openai",
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response (streaming):**
```
data: {"choices":[{"delta":{"content":"Hi"}}]}
data: {"choices":[{"delta":{"content":" there"}}]}
data: {"choices":[{"delta":{"content":"!"}}]}
data: [DONE]
```

**Response (non-streaming):**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Hi there!"
    }
  }],
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5
  }
}
```

---

## Provider Endpoints

### GET /providers

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "providers": [
    {
      "id": "llama.cpp",
      "name": "llama.cpp (Local)",
      "baseUrl": "http://localhost:8080/v1",
      "hasApiKey": false,
      "isDefault": true,
      "models": ["default"]
    },
    {
      "id": "openai",
      "name": "OpenAI",
      "baseUrl": "https://api.openai.com/v1",
      "hasApiKey": true,
      "isDefault": false,
      "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
    }
  ]
}
```

---

### POST /providers/test

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "id": "openai",
  "baseUrl": "https://api.openai.com/v1",
  "apiKey": "sk-..."
}
```

**Response (200):**
```json
{
  "success": true,
  "models": ["gpt-4o", "gpt-4o-mini"]
}
```

---

## Settings Endpoints

### GET /settings

**Headers:** `Authorization: Bearer <accessToken>`

**Response (200):**
```json
{
  "theme": "dark",
  "activeProvider": "openai",
  "providers": {
    "openai": {
      "apiKey": "sk-***masked***",
      "model": "gpt-4o"
    }
  },
  "chatOptions": {
    "temperature": 0.7,
    "maxTokens": 2000,
    "systemMessage": "You are a helpful assistant."
  }
}
```

---

### PUT /settings

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "activeProvider": "gemini",
  "providers": {
    "gemini": {
      "apiKey": "AIza...",
      "model": "gemini-2.0-flash"
    }
  }
}
```

**Response (200):**
```json
{
  "message": "Settings updated"
}
```

---

## MCP Endpoints (Placeholder)

> **Status**: These endpoints return empty/stub responses until MCP is implemented.

### GET /mcp/servers

**Response (200):**
```json
{
  "servers": [],
  "message": "MCP integration coming soon"
}
```

---

### POST /mcp/servers

**Response (501):**
```json
{
  "error": "MCP integration not yet implemented",
  "expectedPhase": 7
}
```

---

### GET /mcp/servers/:id/tools

**Response (200):**
```json
{
  "tools": []
}
```

---

### POST /mcp/tools/call

**Response (501):**
```json
{
  "error": "MCP integration not yet implemented"
}
```

---

## Query Service Endpoints (Python AI Service)

> **Base URL**: Python AI service (default port 8001)

### POST /query/process

Process a query with spelling correction and LLM rewriting.

**Request:**
```json
{
  "query": "how does teh auth wrk?",
  "context": "optional conversation context",
  "auto_confirm": false,
  "enable_rewrite": true,
  "enable_spell_check": true
}
```

**Response (200):**
```json
{
  "original_query": "how does teh auth wrk?",
  "processed_query": "How does the authentication system work, including login and session management?",
  "status": "pending_review",
  "corrections": [
    {"original": "teh", "corrected": "the", "type": "spelling"},
    {"original": "wrk", "corrected": "work", "type": "spelling"},
    {"type": "rewrite", "reason": "LLM optimization"}
  ],
  "confidence": 0.85,
  "requires_confirmation": true,
  "message": "Query was modified. Please review the changes."
}
```

**Status Values:**
- `ready` - Query ready for retrieval
- `pending_review` - Awaiting human confirmation
- `modified` - Query was modified (auto-confirmed)
- `original` - No changes made

---

### POST /query/confirm

Confirm or modify a pending query.

**Request:**
```json
{
  "query_id": "uuid",
  "confirmed": true,
  "modified_query": null
}
```

**Response (200):**
```json
{
  "query": "How does the authentication system work?",
  "status": "ready",
  "message": "Query changes confirmed."
}
```

---

### POST /query/process-and-retrieve

Combined workflow: process query and retrieve in one call.

**Request:**
```json
{
  "query": "how does auth work?",
  "auto_confirm": true,
  "top_k": 5,
  "min_score": 0.5
}
```

**Response (200):**
```json
{
  "status": "completed",
  "original_query": "how does auth work?",
  "processed_query": "How does the authentication system work?",
  "corrections": [...],
  "chunks": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "source_name": "auth-docs.md",
      "content": "...",
      "score": 0.89
    }
  ]
}
```

---

## RAG Endpoints (Python AI Service)

### GET /rag/sources

List all document sources for the current user.

**Response (200):**
```json
{
  "sources": [
    {
      "id": "uuid",
      "name": "documentation.pdf",
      "type": "file",
      "file_size": 102400,
      "chunk_count": 45,
      "created_at": "2026-01-17T00:00:00Z"
    }
  ]
}
```

---

### POST /rag/ingest

Ingest text content into the RAG system.

**Request:**
```json
{
  "name": "my-document",
  "content": "Document text content...",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "metadata": {}
}
```

**Response (201):**
```json
{
  "source_id": "uuid",
  "name": "my-document",
  "chunk_count": 12,
  "message": "Successfully ingested 12 chunks"
}
```

---

### POST /rag/ingest/file

Upload and ingest a document file.

**Request:** `multipart/form-data`
- `file`: File (`.txt`, `.md`, `.pdf`, `.docx`, `.html`)
- `chunk_size`: int (default 500)
- `chunk_overlap`: int (default 50)

**Response (201):**
```json
{
  "source_id": "uuid",
  "name": "document.pdf",
  "chunk_count": 45,
  "message": "Successfully ingested 45 chunks from document.pdf"
}
```

---

### POST /rag/retrieve

Vector similarity search - retrieve relevant chunks.

**Request:**
```json
{
  "query": "How does authentication work?",
  "top_k": 5,
  "min_score": 0.5,
  "source_ids": ["uuid1", "uuid2"]
}
```

**Response (200):**
```json
[
  {
    "id": "uuid",
    "source_id": "uuid",
    "content": "Authentication is handled via JWT tokens...",
    "score": 0.92,
    "metadata": {"source_name": "auth-docs.md"}
  }
]
```

---

### POST /rag/query

RAG query with optional LLM answer generation.

**Request:**
```json
{
  "query": "How does authentication work?",
  "top_k": 5,
  "min_score": 0.5,
  "include_sources": true,
  "generate": true
}
```

**Response (200):**
```json
{
  "query": "How does authentication work?",
  "answer": "Based on the documentation, authentication is handled via JWT tokens. When a user logs in, the system generates an access token (15 min) and refresh token (7 days)...",
  "citations": [
    {
      "source_id": "uuid",
      "source_name": "auth-docs.md",
      "score": 0.92,
      "content_preview": "Authentication is handled via JWT..."
    }
  ],
  "model": "default",
  "chunks": [...],
  "error": null
}
```

---

### DELETE /rag/sources/:id

Delete a document source and all its chunks.

**Response (200):**
```json
{
  "message": "Source deleted successfully"
}
```

---

## Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": {
      "field": "email"
    }
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR` (400)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `NOT_FOUND` (404)
- `CONFLICT` (409)
- `RATE_LIMITED` (429)
- `NOT_IMPLEMENTED` (501)
- `SERVER_ERROR` (500)

---

## TypeScript Interfaces

```typescript
interface User {
  id: string;
  email: string;
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

interface Conversation {
  id: string;
  name: string;
  createdAt: string;
  lastModified: string;
  messageCount?: number;
}

interface Message {
  id: string;
  convId: string;
  parentId: string | null;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: 'text';
  model?: string;
  timestamp: number;
  extra?: any;
}

interface Provider {
  id: string;
  name: string;
  baseUrl: string;
  hasApiKey: boolean;
  isDefault: boolean;
  models: string[];
}

interface Settings {
  theme: 'light' | 'dark';
  activeProvider: string;
  providers: Record<string, ProviderSettings>;
  chatOptions: ChatOptions;
}
```

---

## RAG Endpoints (Python AI Service - Port 8001)

### POST /api/rag/ingest

Ingest text content into the RAG system.

**Request:**
```json
{
  "name": "company-policy",
  "content": "Your document text here...",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "metadata": {"category": "policy"}
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | required | Document name |
| content | string | required | Text content |
| chunk_size | int | 500 | Characters per chunk |
| chunk_overlap | int | 50 | Overlap between chunks |
| metadata | object | {} | Custom metadata |

**Response (200):**
```json
{
  "source_id": "uuid",
  "name": "company-policy",
  "chunk_count": 12,
  "message": "Successfully ingested 12 chunks"
}
```

---

### POST /api/rag/ingest/file

Upload and ingest a file.

**Request:** `multipart/form-data`
- `file`: The file to upload (.txt, .md, .pdf, .docx, .html)
- `chunk_size`: Optional, default 500
- `chunk_overlap`: Optional, default 50

**Response (200):** Same as `/ingest`

**Supported File Types:** `.txt`, `.md`, `.pdf`, `.docx`, `.html`, `.htm`

---

### POST /api/rag/query

Search documents and optionally generate an answer.

**Request:**
```json
{
  "query": "What is the refund policy?",
  "top_k": 5,
  "min_score": 0.5,
  "use_hybrid": true,
  "use_reranking": true,
  "generate": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| query | string | required | Your question |
| top_k | int | 5 | Number of chunks to retrieve |
| min_score | float | 0.5 | Minimum relevance (0-1) |
| use_hybrid | bool | true | BM25 + vector search |
| use_reranking | bool | true | Cross-encoder reranking |
| generate | bool | true | Generate AI answer |

**Response (200):**
```json
{
  "query": "What is the refund policy?",
  "chunks": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "content": "Refunds are processed within 7 days...",
      "score": 0.85,
      "metadata": {"source_name": "policy.pdf"}
    }
  ],
  "answer": "The refund policy states that...",
  "citations": [
    {"source_id": "uuid", "source_name": "policy.pdf", "score": 0.85}
  ],
  "search_mode": "hybrid+rerank"
}
```

---

### POST /api/rag/retrieve

Vector search only (no answer generation).

**Request:**
```json
{
  "query": "authentication",
  "top_k": 5,
  "min_score": 0.5,
  "source_ids": ["uuid1", "uuid2"]
}
```

**Response (200):** Array of chunks

---

### GET /api/rag/sources

List all ingested documents for the current user.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "company-policy",
    "type": "text",
    "chunk_count": 12,
    "created_at": "2025-01-17T00:00:00Z"
  }
]
```

---

### DELETE /api/rag/sources/{source_id}

Delete a document and all its chunks.

**Response (200):**
```json
{"deleted": true}
```

---

## Query Preprocessing Endpoints

### POST /api/query/process

Preprocess a query (spelling correction, rewriting).

**Request:**
```json
{"query": "wat is autentication?"}
```

**Response (200):**
```json
{
  "original_query": "wat is autentication?",
  "processed_query": "What is authentication?",
  "corrections": [
    {"original": "wat", "corrected": "what"},
    {"original": "autentication", "corrected": "authentication"}
  ],
  "requires_confirmation": true,
  "session_id": "uuid"
}
```

### POST /api/query/confirm

Confirm or modify a processed query.

**Request:**
```json
{
  "session_id": "uuid",
  "confirmed_query": "What is authentication?",
  "user_accepted": true
}
```

---

## RAG TypeScript Interfaces

```typescript
interface RAGSource {
  id: string;
  name: string;
  type: 'text' | 'file';
  chunkCount: number;
  createdAt: string;
}

interface RAGChunk {
  id: string;
  sourceId: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

interface RAGQueryRequest {
  query: string;
  topK?: number;
  minScore?: number;
  useHybrid?: boolean;
  useReranking?: boolean;
  generate?: boolean;
}

interface RAGQueryResponse {
  query: string;
  chunks: RAGChunk[];
  answer?: string;
  citations?: Citation[];
  searchMode: 'vector' | 'hybrid' | 'hybrid+rerank';
}
```
