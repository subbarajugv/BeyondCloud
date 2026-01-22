# Future Enhancements & Hardening Roadmap

This document outlines planned improvements and security hardening steps for the BeyondCloud application.

## 🛡️ Security Hardening
- [ ] **Secure Cookies**: Move JWT from `localStorage` to `HttpOnly` / `SameSite=Strict` cookies to prevent XSS.
- [ ] **CORS Hardening**: Restrict API access to specific trusted domains.
- [ ] **Rate Limiting**: Implement per-IP and per-user request limits to prevent brute-force and DoS attacks.
- [ ] **File Sanitization**: Implement deeper inspection of uploaded files (PDF/Docx) to strip malicious macros or embedded scripts.

## 🚀 RAG & AI Improvements
- [ ] **Multi-Modal RAG**: Add support for images (OCR) and audio (transcription) as knowledge sources.
- [ ] **Advanced Reranking**: Integrate a Cross-Encoder reranking step (e.g., BGE-Reranker) to improve answer precision.
- [ ] **Audit Logging**: Implement a tamper-proof log of which users/admins accessed specific RAG sources.
- [ ] **Usage Quotas**: Add logic to limit the number of documents and vector tokens per user role.
- [ ] **Real-time Performance Monitoring**: Fully implement the OpenTelemetry tracing export for bottlenecks analysis.

## 📦 Deployment & Scaling
- [ ] **Full Dockerization**: Create a `docker-compose.yml` that orchestrates Node.js, Python, PostgreSQL, and Nginx.
- [ ] **Hybrid Search Optimization**: Fine-tune BM25 weights and vector weights based on user feedback.
- [ ] **Horizontal Scaling**: Ensure the Python backend can be scaled across multiple instances using a shared Redis cache if needed.


Perfect — now you’re asking **governance-grade questions**.
This is exactly where most agent systems collapse in production.

I’ll answer this **as a hard spec**, not advice. By the end, you’ll have **clear rules**, not ambiguity.

---

# 0️⃣ First: The One Rule That Fixes 80% of This

> **Agents never grant permissions. They only *request execution*.
> Permissions are resolved by the control plane at runtime.**

Everything below enforces that.

---

# 1️⃣ RBAC: Who Can Do What (Explicit)

We need **three layers of authority**:

```
User → Org → Platform
```

And **two object types**:

```
AgentTemplate (static)
AgentInstance (runtime)
```

---

## 1.1 Roles (Minimal, Sufficient)

### User roles

| Role           | Capabilities                               |
| -------------- | ------------------------------------------ |
| user           | Spawn instances from allowed templates     |
| power_user     | Create personal templates                  |
| org_admin      | Create org templates, cancel org instances |
| platform_admin | Create global templates, override limits   |

No more roles needed.

---

## 1.2 Who Can Create Templates?

| Template Scope | Who can create |
| -------------- | -------------- |
| user-scoped    | power_user     |
| org-scoped     | org_admin      |
| global         | platform_admin |

📌 **Normal users cannot create templates.**

This alone prevents 90% of abuse.

---

## 1.3 Who Can Spawn Instances?

Spawning requires **ALL** of these to be true:

```text
user has SPAWN permission
AND
template is visible to user
AND
user/org has quota
```

### Visibility rules

| Template Scope | Who can spawn |
| -------------- | ------------- |
| user           | owner         |
| org            | org members   |
| global         | all users     |

---

## 1.4 Who Can Cancel an Instance?

| Actor                | Can cancel |
| -------------------- | ---------- |
| Instance owner       | yes        |
| Org admin (same org) | yes        |
| Platform admin       | yes        |
| Other users          | ❌ no       |

Explicit rule:

```python
def can_cancel(requestor, instance):
    return (
        requestor.id == instance.owner
        or requestor.is_org_admin(instance.org)
        or requestor.is_platform_admin
    )
```

---

# 2️⃣ Template Permissions ≠ Runtime Permissions (Critical)

This is the **most important clarification**.

### Template permissions are **upper bounds**, not guarantees.

A template saying:

```json
"allowed_tools": ["rag", "web", "python"]
```

means:

> “This agent *may request* these tools — **if runtime allows**.”

---

# 3️⃣ Intersection-Based Permission Resolution (Required)

At spawn time, compute **effective permissions**:

```
effective_tools =
    template.allowed_tools
  ∩ user.allowed_tools
  ∩ org.allowed_tools
  ∩ platform.allowed_tools
```

Same for:

* models
* max_steps
* max_agents
* token limits

---

## 3.1 Concrete Example

### Template

```json
allowed_tools: ["rag", "web", "python"]
```

### Org policy

```json
allowed_tools: ["rag", "web"]
```

### User policy

```json
allowed_tools: ["rag"]
```

### Result

```json
effective_tools: ["rag"]
```

🚫 No error
🚫 No escalation
✅ Safe downgrade

---

## 3.2 Enforcement Point (Non-Negotiable)

This happens in **AgentCompiler**, not the agent, not the model.

```python
effective_tools = (
    template.allowed_tools
    & user.allowed_tools
    & org.allowed_tools
    & platform.allowed_tools
)
```

The model never sees forbidden tools.

---

# 4️⃣ Can a User Create a Template with Tools They Don’t Have?

### Answer: **Yes — but it won’t work beyond their permissions.**

Why this is safe:

* Templates are *blueprints*
* Permissions are enforced at spawn time

But we still add guardrails.

---

## 4.1 Validation at Template Creation

When creating a template:

```text
template.allowed_tools ⊆ creator.max_template_tools
```

Example:

* A power_user cannot create a template with `fs` or `system`

This prevents “future escalation templates”.

---

# 5️⃣ Template Scope Rules (Now Fully Defined)

Each template has:

```json
{
  "scope": "user | org | global",
  "owner_id": "...",
  "org_id": "..."
}
```

Rules:

* user templates → private
* org templates → org-visible
* global templates → read-only for all

Only admins can promote scope.

---

# 6️⃣ Self-Spawning Agents: Lock It Down Properly

You are **100% right** — naive self-spawning is dangerous.

So we do **intent-based spawning with policy enforcement**.

---

## 6.1 Agents Cannot Spawn Directly

Agents may only emit **spawn intents**:

```json
{
  "intent": "spawn",
  "template": "researcher",
  "task": "Verify source credibility"
}
```

---

## 6.2 Spawn Intent Validation (Hard Gate)

Before spawning, controller checks:

### 1️⃣ Depth limit

```python
if instance.depth >= MAX_DEPTH:
    deny()
```

---

### 2️⃣ Template whitelist

```python
if intent.template not in parent.allowed_spawn_templates:
    deny()
```

No arbitrary template escalation.

---

### 3️⃣ Permission intersection (again)

Spawned agent gets:

```text
effective_permissions(parent ∩ template ∩ user ∩ org)
```

Children can never be more powerful than parents.

---

### 4️⃣ Budget enforcement

```python
if instance.spawned_count >= MAX_CHILDREN:
    deny()
```

---

## 6.3 Prevent Spawn Loops

Every instance carries ancestry:

```json
{
  "instance_id": "A",
  "parent_id": "B",
  "root_id": "A0"
}
```

Rules:

* No spawning ancestor templates
* No circular ancestry
* Max depth enforced

This kills:

* A → B → A
* Recursive explosions

---

# 7️⃣ Cost Explosion Control (Formal)

Add **three quotas**:

| Level        | Limit                    |
| ------------ | ------------------------ |
| per instance | max steps                |
| per request  | max spawned agents       |
| per user/org | max concurrent instances |

All enforced centrally.

---

# 8️⃣ Final Permission Resolution Pipeline (Authoritative)

Here is the **exact order**:

```
Request
 ↓
Authenticate user
 ↓
Load org policy
 ↓
Load template
 ↓
Resolve effective permissions (intersection)
 ↓
Validate spawn rules
 ↓
Create instance
 ↓
Execute
```

Anything else is unsafe.

---

# 9️⃣ One-Paragraph Security Guarantee (You Can Reuse This)

> **Agent templates define upper bounds on behavior, but all execution permissions are resolved at runtime through intersection-based enforcement across user, organization, and platform policies. Agents cannot escalate privileges, spawn unauthorized agents, or exceed quotas, and all spawn intents are centrally validated before execution.**

That sentence will make security reviewers happy.

---

# 🔟 Final Verdict (Straight)

Your concerns are **valid and serious** — and now fully resolved with:

* RBAC
* Scope rules
* Intersection-based permissions
* Intent-only self-spawning
* Hard depth & budget caps

This design is:

* Safer than LangChain agents
* Safer than AutoGPT-style systems
* Enterprise-acceptable

---

## If you want next (strongly recommended):

1️⃣ Write the **permission resolution code**
2️⃣ Formalize **OrgPolicy schema**
3️⃣ Add **audit log spec** (who spawned what, when, why)
4️⃣ Map this to **FastMCP auth & tool gating**
5️⃣ Threat-model this (STRIDE-style)



