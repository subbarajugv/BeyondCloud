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

### PUT /conversations/:convId/messages/:msgId

Updates a message's content (used after streaming completes).

**Headers:** `Authorization: Bearer <accessToken>`

**Request:**
```json
{
  "content": "Updated message content",
  "reasoning_content": "Optional reasoning/thinking content",
  "model": "gemma3:12b"
}
```

**Response (200):**
```json
{
  "message": {
    "id": "uuid",
    "parent_id": "uuid",
    "role": "assistant",
    "content": "Updated message content",
    "model": "gemma3:12b",
    "reasoning_content": "Optional reasoning content",
    "created_at": "2025-01-11T10:00:00Z"
  }
}
```

**Errors:** `400` (no fields to update), `404` (conversation/message not found)

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
