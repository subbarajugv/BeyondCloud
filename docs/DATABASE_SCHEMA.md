# BeyondCloud Database Schema & ER Diagram

This document provides a map of the database structure and an evaluation of its robustness and security features.

## ER Diagram

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : "has"
    USERS ||--o{ REFRESH_TOKENS : "manages"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "manages"
    USERS ||--|| USER_SETTINGS : "customizes"
    USERS ||--o{ RAG_COLLECTIONS : "owns"
    USERS ||--o{ RAG_SOURCES : "owns"
    USERS ||--o{ TRACES : "generates"

    CONVERSATIONS ||--o{ MESSAGES : "contains"
    MESSAGES |o--o| MESSAGES : "parent (branching)"
    CONVERSATIONS |o--o| MESSAGES : "current_node"

    RAG_COLLECTIONS ||--o{ RAG_COLLECTIONS : "parent (nesting)"
    RAG_COLLECTIONS ||--o{ RAG_SOURCES : "contains"
    RAG_SOURCES ||--o{ RAG_CHUNKS : "contains"

    USERS {
        uuid id PK
        string email UK
        string password_hash
        string display_name
        string role
        timestamp created_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string name
        uuid current_node FK
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        uuid parent_id FK
        string role
        text content
        jsonb extra
    }

    RAG_COLLECTIONS {
        uuid id PK
        uuid parent_id FK
        uuid user_id FK
        string name
        string visibility
        text[] allowed_roles
        uuid[] allowed_teams
        uuid[] allowed_users
    }

    RAG_SOURCES {
        uuid id PK
        uuid collection_id FK
        uuid user_id FK
        string name
        string visibility
        string storage_key
        string storage_type
        jsonb metadata
    }

    RAG_CHUNKS {
        uuid id PK
        uuid source_id FK
        text content
        vector embedding
    }

    TRACES {
        string span_id PK
        string trace_id
        uuid user_id FK
        jsonb attributes
    }
```

## Robustness & Security Analysis

### 1. Identity & Access Control
- **User IDs (UUIDs)**: Every table containing user data uses a `user_id` linked back to the `users` table.
- **Secure IDs**: We use **UUID v4** (random) instead of sequential integers. This prevents "ID enumeration" attacks.
- **Authentication Linking**: API endpoints verify the JWT token, extract the `user_id`, and then query the database using that ID.

### 2. Data Integrity
- **Foreign Keys**: We use `REFERENCES` constraints everywhere.
- **Cascading Deletes**: Most relationships use `ON DELETE CASCADE`. If a user deletes a conversation, all its messages are purged.
- **Triggers**: PostgreSQL triggers automatically update `updated_at` timestamps.

### 3. RAG Visibility
- **Isolation**: RAG queries filter by `(user_id = :current_user OR visibility = 'shared')`.

### 4. Performance
- **Indexing**: Indices on `user_id`, `conversation_id`, and `email` for fast lookups.
- **Vector Indexing**: especializados indices for `pgvector` columns.

### 5. Session Security
- **Token Rotation**: The `refresh_tokens` table tracks active sessions.
- **Password Safety**: Stored using `bcrypt` hashes.
