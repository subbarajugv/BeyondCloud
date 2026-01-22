# Internal Issue Tracker for BeyondCloud

> **Dog-food your own product** - Extend the existing ticket system to track development issues, demonstrating product maturity and enabling AI-powered issue management.

---

## Design Decisions

### Why a Separate `issues` Table vs. Extending `support_tickets`?

| Approach | Pros | Cons |
|----------|------|------|
| **Extend `support_tickets`** | Less migration | Pollutes user-facing support with dev issues |
| **New `issues` table** ✅ | Clean separation, purpose-built schema | One more table |

**Decision**: Create a new `issues` table. This keeps user support tickets separate from internal development tracking and allows purpose-built fields.

---

## Proposed Changes

### Database Schema

#### [NEW] `issues` table in [database.py](file:///home/subba/llama.cpp/llamacpp-auth-webui/backend-python/app/database.py)

```sql
CREATE TABLE IF NOT EXISTS issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    number SERIAL,                              -- Human-readable BC-1, BC-2, etc.
    title VARCHAR(255) NOT NULL,
    description TEXT,
    issue_type VARCHAR(20) NOT NULL DEFAULT 'bug',  -- 'bug' | 'feature' | 'optimization' | 'docs'
    
    -- Status & Priority
    status VARCHAR(20) DEFAULT 'open',          -- 'open' | 'in_progress' | 'resolved' | 'closed'
    priority VARCHAR(10) DEFAULT 'medium',      -- 'p0' | 'p1' | 'p2' | 'p3'
    
    -- Labels (flexible tagging)
    labels TEXT[] DEFAULT '{}',                 -- ['pagination', 'dashboard', 'ui']
    
    -- Milestone linking
    milestone VARCHAR(20),                      -- 'v0.6.0', 'v0.7.0', etc.
    
    -- Git integration
    linked_commits TEXT[] DEFAULT '{}',         -- ['abc123', 'def456']
    linked_prs TEXT[] DEFAULT '{}',             -- ['#42', '#43']
    
    -- Relationships
    created_by UUID,                            -- User who created
    assigned_to UUID,                           -- User assigned (nullable)
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_milestone ON issues(milestone);
CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues(priority);
CREATE INDEX IF NOT EXISTS idx_issues_labels ON issues USING GIN(labels);
CREATE UNIQUE INDEX IF NOT EXISTS idx_issues_number ON issues(number);
```

---

### Backend API

#### [NEW] [issues.py](file:///home/subba/llama.cpp/llamacpp-auth-webui/backend-python/app/routers/issues.py)

| Endpoint | Method | RBAC | Description |
|----------|--------|------|-------------|
| `/api/issues` | GET | `rag_user+` | List all issues (with filters) |
| `/api/issues` | POST | `rag_user+` | Create new issue |
| `/api/issues/{id}` | GET | `rag_user+` | Get issue details |
| `/api/issues/{id}` | PUT | `rag_user+` | Update issue |
| `/api/issues/{id}` | DELETE | `admin` | Delete issue |
| `/api/issues/{id}/assign` | POST | `admin` | Assign to user |
| `/api/issues/{id}/link-commit` | POST | `rag_user+` | Link a commit hash |
| `/api/issues/milestones` | GET | public | List all milestones |
| `/api/issues/labels` | GET | public | List all unique labels |

**Query Parameters for GET `/api/issues`:**
- `status`: Filter by status
- `milestone`: Filter by milestone
- `label`: Filter by label (can repeat for OR)
- `priority`: Filter by priority
- `issue_type`: Filter by type
- `limit`, `offset`: Pagination

---

### Frontend Components

#### [NEW] [IssueTracker.svelte](file:///home/subba/llama.cpp/llamacpp-auth-webui/frontend/src/lib/components/admin/IssueTracker.svelte)

A dashboard component with:
- **Issue List View**: Filterable table with status badges, priority indicators
- **Kanban Board View**: Drag-drop columns (Open → In Progress → Resolved)
- **Issue Detail Modal**: Full description, comments (future), linked commits
- **Quick Actions**: Create, assign, link commit, change status

#### [MODIFY] [AdminDashboard.svelte](file:///home/subba/llama.cpp/llamacpp-auth-webui/frontend/src/lib/components/admin/AdminDashboard.svelte)

Add "Issues" tab alongside existing Users/Tickets tabs.

---

### Release Notes Integration

#### [MODIFY] [RELEASE_NOTES.md](file:///home/subba/llama.cpp/llamacpp-auth-webui/RELEASE_NOTES.md)

Format for linking:

```markdown
## Known Limitations / Risks
1. **Ticket System**: Basic CRUD only. [BC-12](/issues/12)
2. **Dashboard Performance**: Pagination needed. [BC-15](/issues/15)
```

The `BC-###` format creates clickable links when viewing in the admin panel.

---

## Verification Plan

### Automated Tests

```bash
# Backend API tests
cd backend-python
pytest tests/test_issues.py -v

# Frontend build verification
cd frontend
npm run build
```

### Manual Verification

1. Create an issue via API or UI
2. Verify it appears with correct `BC-###` number
3. Add labels and milestone
4. Link a commit hash
5. Change status to resolved
6. Verify in admin dashboard

---

## Future Enhancements (Not in Scope)

- **MCP Server for Issues**: Allow AI agents to query/create issues
- **GitHub Sync**: Two-way sync with GitHub Issues
- **Email Notifications**: Notify on assignment/status change
- **Comments/Activity Log**: Full issue history
- **SLA Tracking**: Response time metrics

---

## Summary

This implementation:
1. ✅ Dog-foods your own product
2. ✅ Enterprise-hardened (RBAC, proper schema, indexes)
3. ✅ Git-integrated (linked commits/PRs)
4. ✅ Milestone-aware (v0.6.0, v0.7.0)
5. ✅ Release notes friendly (BC-### linking format)
6. ✅ AI-ready (structured data for future MCP integration)
