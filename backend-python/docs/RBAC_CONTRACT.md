# Access Control Contract (RBAC)

**Version**: 1.0  
**Status**: Draft  
**Last Updated**: 2026-01-11

Role-Based Access Control for Agents, RAG, and system resources.

---

## Role Hierarchy

```
Super Admin
     │
     ├── Admin
     │      │
     │      ├── Agent Developer
     │      │
     │      └── Data Manager
     │
     └── User
            │
            └── Viewer (Read-only)
```

---

## Role Definitions

| Role | Description | Scope |
|------|-------------|-------|
| `super_admin` | Full system access | Global |
| `admin` | Org-level management | Organization |
| `agent_developer` | Create/deploy agents | Organization |
| `data_manager` | Manage RAG ingestion | Organization |
| `user` | Use agents and RAG | Self + shared |
| `viewer` | Read-only access | Self + shared |

---

## Permission Matrix

### Chat & Conversation Permissions

| Permission | Super Admin | Admin | Agent Dev | Data Mgr | User | Viewer |
|------------|-------------|-------|-----------|----------|------|--------|
| Chat with LLM | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| View own conversations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Delete own conversations | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| View all org conversations | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

### Agent Permissions

| Permission | Super Admin | Admin | Agent Dev | Data Mgr | User | Viewer |
|------------|-------------|-------|-----------|----------|------|--------|
| **Use Agents** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| View available agents | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Create agent** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Deploy agent** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit own agents | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete own agents | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit any agent | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete any agent | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| View agent logs | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Configure agent tools | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

### RAG Permissions

| Permission | Super Admin | Admin | Agent Dev | Data Mgr | User | Viewer |
|------------|-------------|-------|-----------|----------|------|--------|
| **Access RAG** | ✅ | ✅ | ✅ | ✅ | ✅* | ❌ |
| **Ingest documents** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| View ingestion jobs | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Delete ingested docs | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Create data sources | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Configure embeddings | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| View RAG usage stats | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |

*User RAG access controlled by Data Source permissions (see below)

---

### Data Source Permissions

| Permission | Super Admin | Admin | Agent Dev | Data Mgr | User | Viewer |
|------------|-------------|-------|-----------|----------|------|--------|
| Create data source | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Set data source visibility | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Query public data sources | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Query private data sources | ✅ | ✅ | Assigned | Assigned | Assigned | Assigned |

---

### System Permissions

| Permission | Super Admin | Admin | Agent Dev | Data Mgr | User | Viewer |
|------------|-------------|-------|-----------|----------|------|--------|
| Manage users | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign roles | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Configure providers | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| View audit logs | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| System settings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Data Source Access Model

Data sources can be scoped:

| Visibility | Who Can Query |
|------------|---------------|
| `public` | All org users |
| `role` | Users with specific roles |
| `team` | Users in specific teams |
| `private` | Only assigned users |
| `personal` | Only the owner |

### Data Source Schema

```typescript
interface DataSource {
  id: string;
  name: string;
  ownerId: string;
  organizationId: string;
  visibility: 'public' | 'role' | 'team' | 'private' | 'personal';
  allowedRoles?: string[];      // If visibility = 'role'
  allowedTeams?: string[];      // If visibility = 'team'
  allowedUsers?: string[];      // If visibility = 'private'
  createdAt: Date;
}
```

---

## Agent Access Model

Agents can be scoped:

| Visibility | Who Can Use |
|------------|-------------|
| `public` | All org users |
| `role` | Users with specific roles |
| `private` | Only assigned users |
| `draft` | Only the creator |

### Agent Schema

```typescript
interface Agent {
  id: string;
  name: string;
  creatorId: string;
  organizationId: string;
  status: 'draft' | 'deployed' | 'disabled';
  visibility: 'public' | 'role' | 'private' | 'draft';
  allowedRoles?: string[];
  allowedUsers?: string[];
  tools: string[];
  dataSources: string[];  // RAG data sources this agent can access
}
```

---

## API Authorization

### Middleware Contract

```typescript
interface AuthMiddleware {
  // Check if user has permission
  hasPermission(userId: string, permission: string): Promise<boolean>;
  
  // Check if user can access resource
  canAccess(userId: string, resourceType: string, resourceId: string): Promise<boolean>;
  
  // Get user's effective permissions
  getPermissions(userId: string): Promise<string[]>;
}
```

### Authorization Headers

```
Authorization: Bearer <jwt>
X-Organization-Id: <org-id>  (for multi-org users)
```

---

## API Responses for Access Denied

| Code | Error | Meaning |
|------|-------|---------|
| 401 | `UNAUTHORIZED` | Not logged in |
| 403 | `FORBIDDEN` | Logged in but no permission |
| 403 | `ROLE_REQUIRED` | Need specific role |
| 403 | `RESOURCE_NOT_ACCESSIBLE` | Resource visibility restriction |

### Error Response

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to deploy agents",
    "requiredRole": "agent_developer",
    "currentRoles": ["user"]
  }
}
```

---

## Database Schema

```sql
-- Roles table
CREATE TABLE roles (
  id UUID PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  permissions JSONB NOT NULL,
  is_system BOOLEAN DEFAULT FALSE
);

-- User roles (many-to-many)
CREATE TABLE user_roles (
  user_id UUID REFERENCES users(id),
  role_id UUID REFERENCES roles(id),
  organization_id UUID REFERENCES organizations(id),
  granted_by UUID REFERENCES users(id),
  granted_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id, organization_id)
);

-- Data source access
CREATE TABLE data_source_access (
  data_source_id UUID REFERENCES data_sources(id),
  access_type VARCHAR(20) NOT NULL, -- 'user', 'role', 'team'
  access_id UUID NOT NULL,          -- user_id, role_id, or team_id
  permission VARCHAR(20) NOT NULL,  -- 'read', 'write', 'admin'
  PRIMARY KEY (data_source_id, access_type, access_id)
);

-- Agent access
CREATE TABLE agent_access (
  agent_id UUID REFERENCES agents(id),
  access_type VARCHAR(20) NOT NULL,
  access_id UUID NOT NULL,
  PRIMARY KEY (agent_id, access_type, access_id)
);
```

---

## Default Roles

On organization creation:

| Role | Default Permissions |
|------|---------------------|
| `admin` | All except system settings |
| `user` | Chat, use public agents, query public data |
| `viewer` | Read-only access |

---

## Contract Guarantees

1. **Isolation**: Users cannot access other orgs' data
2. **Least Privilege**: Minimum permissions by default
3. **Audit Trail**: All permission changes logged
4. **Role Inheritance**: Higher roles include lower permissions
5. **Resource Scoping**: Permissions checked at resource level

---

## Contract Failures

| Code | Meaning |
|------|---------|
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | Insufficient permissions |
| `ROLE_NOT_FOUND` | Invalid role specified |
| `ASSIGNMENT_FAILED` | Cannot assign role |

---

## Compliance Checklist

- [ ] Roles table created
- [ ] User-role assignment implemented
- [ ] Permission check middleware
- [ ] Agent access control
- [ ] Data source access control
- [ ] RAG query filtering by access
- [ ] Audit logging
