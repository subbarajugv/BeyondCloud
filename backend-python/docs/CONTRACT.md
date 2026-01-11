# API Contract

**Version**: 1.0  
**Status**: Active  
**Last Updated**: 2026-01-11

This document defines the formal contract between frontend and backend. Both parties MUST adhere to this contract.

---

## Contract Summary

| Aspect | Specification |
|--------|---------------|
| **Protocol** | HTTP/HTTPS |
| **Format** | JSON (Content-Type: application/json) |
| **Auth** | Bearer token in Authorization header |
| **Base Path** | `/api` |

---

## 1. INPUTS (What Frontend Sends)

### Request Format

```
METHOD /api/endpoint HTTP/1.1
Host: api.example.com
Content-Type: application/json
Authorization: Bearer <access_token>  ← Required for protected routes

{ "json": "body" }
```

### Input Validation Rules

| Field | Validation | Error if Invalid |
|-------|------------|------------------|
| `email` | Valid email format | 400 VALIDATION_ERROR |
| `password` | Min 8 chars, 1 upper, 1 lower, 1 digit | 400 VALIDATION_ERROR |
| `messages` | Non-empty array | 400 VALIDATION_ERROR |
| `Authorization` | Valid JWT, not expired | 401 UNAUTHORIZED |

### Required Headers

| Header | When Required | Value |
|--------|---------------|-------|
| `Content-Type` | POST/PUT requests | `application/json` |
| `Authorization` | Protected routes | `Bearer <token>` |

---

## 2. OUTPUTS (What Backend Returns)

### Success Response Format

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-01-11T10:00:00Z"
  }
}
```

### Response by Endpoint

| Endpoint | Success Code | Response Shape |
|----------|--------------|----------------|
| `POST /auth/register` | 201 | `{ user, message }` |
| `POST /auth/login` | 200 | `{ accessToken, refreshToken, expiresIn, user }` |
| `POST /auth/logout` | 200 | `{ message }` |
| `POST /auth/refresh` | 200 | `{ accessToken, expiresIn }` |
| `GET /auth/me` | 200 | `{ id, email, emailVerified, ... }` |
| `GET /conversations` | 200 | `{ conversations: [...] }` |
| `POST /conversations` | 201 | `{ id, name, createdAt }` |
| `GET /messages/:id` | 200 | `{ messages: [...] }` |
| `POST /chat/completions` | 200 | SSE stream or `{ choices: [...] }` |
| `GET /settings` | 200 | `{ theme, activeProvider, ... }` |

---

## 3. GUARANTEES (What Backend Promises)

### Data Guarantees

| Guarantee | Description |
|-----------|-------------|
| **User Isolation** | User A CANNOT access User B's conversations, messages, or settings |
| **Atomic Operations** | Database changes are transactional - all or nothing |
| **Consistency** | GET after POST returns the created resource |
| **Idempotency** | GET and DELETE are safe to retry |

### Security Guarantees

| Guarantee | Description |
|-----------|-------------|
| **Password Storage** | Passwords hashed with bcrypt/argon2 (never plaintext) |
| **Token Security** | JWT signed with secret, verified on every request |
| **Rate Limiting** | Endpoints protected from brute force |
| **Input Sanitization** | All inputs validated and sanitized |

### Response Guarantees

| Guarantee | Description |
|-----------|-------------|
| **Always JSON** | Response body is always valid JSON (except SSE) |
| **Consistent Errors** | All errors follow the error format below |
| **HTTP Semantics** | Correct status codes (2xx success, 4xx client error, 5xx server error) |
| **CORS** | Proper headers for cross-origin requests |

---

## 4. FAILURES (What Can Go Wrong)

### Error Response Format (GUARANTEED)

Every error response follows this exact structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { }
  }
}
```

### Error Codes

| HTTP | Code | Meaning | Frontend Action |
|------|------|---------|-----------------|
| 400 | `VALIDATION_ERROR` | Invalid input | Show validation errors |
| 401 | `UNAUTHORIZED` | Missing/invalid token | Redirect to login |
| 401 | `TOKEN_EXPIRED` | JWT expired | Call refresh endpoint |
| 403 | `FORBIDDEN` | No permission | Show access denied |
| 403 | `EMAIL_NOT_VERIFIED` | Email not verified | Show verification prompt |
| 404 | `NOT_FOUND` | Resource doesn't exist | Show not found |
| 409 | `CONFLICT` | Duplicate resource | Show already exists |
| 423 | `ACCOUNT_LOCKED` | Too many failed attempts | Show locked message |
| 429 | `RATE_LIMITED` | Too many requests | Show retry message |
| 500 | `SERVER_ERROR` | Internal error | Show generic error |
| 502 | `LLM_ERROR` | LLM provider failed | Show provider error |
| 503 | `SERVICE_UNAVAILABLE` | Service down | Show maintenance |

### Failure Recovery

| Error | Frontend Should |
|-------|-----------------|
| 401 TOKEN_EXPIRED | Automatically call `/auth/refresh`, retry original request |
| 401 UNAUTHORIZED | Clear tokens, redirect to login |
| 429 RATE_LIMITED | Wait and retry with exponential backoff |
| 5xx errors | Show error, allow retry |

---

## 5. STREAMING (Chat Completions)

### SSE Format

When `stream: true`:

```
data: {"choices":[{"delta":{"content":"Hello"}}]}

data: {"choices":[{"delta":{"content":" world"}}]}

data: [DONE]
```

### Streaming Guarantees

| Guarantee | Description |
|-----------|-------------|
| **Chunked** | Each `data:` line is a valid JSON object |
| **Ordered** | Chunks arrive in correct order |
| **Complete** | Stream ends with `data: [DONE]` |
| **Error Mid-Stream** | `data: {"error": {...}}` then close |

---

## 6. VERSIONING

| Version | Status | Breaking Changes |
|---------|--------|------------------|
| 1.0 | Current | N/A - Initial release |

### Breaking Change Policy

- Breaking changes require version increment
- Old versions supported for 6 months
- Clients should check `X-API-Version` header

---

## 7. TESTING THE CONTRACT

### Health Check

```bash
curl https://api.example.com/api/health
# Expected: { "status": "ok", "version": "1.0" }
```

### Verify Error Format

```bash
curl -X POST https://api.example.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid"}'
# Expected: 400 with { "error": { "code": "VALIDATION_ERROR", ... } }
```

---

## Contract Compliance

Both frontend and backend teams agree:

- [ ] Frontend will only send inputs as specified
- [ ] Backend will only return outputs as specified  
- [ ] Backend will honor all guarantees
- [ ] Backend will return errors in the specified format
- [ ] Changes require updating this contract first
