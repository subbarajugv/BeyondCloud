# Agent System Expansion Roadmap 🤖

## Current State
- **Single Agent Loop**: ReAct (Reason → Act → Observe)
- **4 Template Agents**: CodingAgent, ResearchAgent, DataAgent, PlanningAgent
- **Tool Discovery**: Dynamic via MCP servers
- **Execution**: Dual-mode (Local/Remote)

## Expansion Ideas

### 1. Multi-Agent Orchestration 🎭
**Problem**: One agent can't do everything well.
**Solution**: Specialized agents that collaborate.

| Pattern | Description | Use Case |
| :--- | :--- | :--- |
| **Supervisor** | One agent routes tasks to specialists | "Fix this bug" → Supervisor → CodingAgent or ResearchAgent |
| **Debate** | Two agents argue, third decides | Code Review: Writer vs Critic |
| **Pipeline** | Agents run in sequence | Planner → Coder → Tester → Reviewer |
| **Swarm** | Parallel agents, merge results | Multi-source research |

**Implementation**:
- Create `AgentOrchestrator` class
- Define `AgentRole` enum (supervisor, worker, critic)
- Add message passing between agents

---

### 2. Long-Term Memory 🧠
**Problem**: Agent forgets everything after each session.
**Solution**: Persistent memory layers.

| Memory Type | Storage | Use Case |
| :--- | :--- | :--- |
| **Episodic** | Postgres/Redis | "Last time you asked about X, I did Y" |
| **Semantic** | pgvector | Embed past conversations for retrieval |
| **Procedural** | JSON/YAML | "When deploying, always run tests first" |

**Implementation**:
- Create `AgentMemory` service
- Store: `(agent_id, user_id, memory_type, embedding, content)`
- Inject relevant memories into system prompt

---

### 3. Workflow Automation (DAG) 📊
**Problem**: Agents are good at ad-hoc tasks, not repeatable workflows.
**Solution**: Define workflows as Directed Acyclic Graphs (DAGs).

```yaml
# Example: PR Review Workflow
name: pr_review
steps:
  - id: fetch
    agent: CodingAgent
    action: "Fetch the PR diff"
  - id: analyze
    agent: DataAgent
    depends_on: [fetch]
    action: "Analyze code complexity"
  - id: review
    agent: PlanningAgent
    depends_on: [analyze]
    action: "Generate review comments"
```

**Implementation**:
- Create `Workflow` class (parse YAML/JSON)
- Create `WorkflowRunner` (executes DAG)
- UI for workflow builder (drag-and-drop)

---

### 4. Specialized Reasoning Architectures 🔬

| Architecture | Description | Best For |
| :--- | :--- | :--- |
| **Chain-of-Thought (CoT)** | Force step-by-step reasoning | Math, Logic |
| **Tree-of-Thought (ToT)** | Explore multiple paths, backtrack | Creative, Planning |
| **ReWOO** | Plan all steps first, then execute | Complex multi-step |
| **LATS** | LLM Agent Tree Search | Game-like decision making |

**Implementation**:
- Add `reasoning_mode` to `AgentConfig`
- Implement `TreeOfThoughtAgent` class

---

### 5. Agent Marketplace 🛒
**Problem**: Users want pre-built agents for specific tasks.
**Solution**: A library of community/enterprise agents.

| Agent | Description |
| :--- | :--- |
| **SEC Analyst** | Parses 10-K filings, extracts financials |
| **Kubernetes Ops** | Diagnoses cluster issues |
| **Legal Review** | Contract clause analysis |
| **HR Onboarding** | Generates onboarding checklists |

**Implementation**:
- Create `AgentTemplate` registry
- Allow import/export of agent configs
- Versioning for agent updates

---

## Recommended Priority

| Phase | Feature | Effort | Impact |
| :--- | :--- | :--- | :--- |
| **Phase A** | Long-Term Memory | Medium | High (Differentiator) |
| **Phase B** | Multi-Agent (Supervisor) | Medium | High (Enterprise) |
| **Phase C** | Workflow DAG | High | High (Automation) |
| **Phase D** | Specialized Reasoning | Low | Medium |
| **Phase E** | Agent Marketplace | Medium | High (Growth) |

---

## Current Architecture Questions

### Q1: Where do Agents Run? (Local vs Cloud)

**Current State**: We have **Dual-Mode Execution**:

| Mode | Where Agent Runs | Where Tools Run | Use Case |
| :--- | :--- | :--- | :--- |
| **Local Mode** | Developer's machine | Local FastMCP | Air-gapped, zero-latency dev |
| **Remote Mode** | Backend Server | Backend MCP | Multi-user, audited, RBAC |

**Gap**: Agent *state* is lost on restart. Fix this in Phase 10 (Backend-Driven Agent).

---

### Q2: RBAC for Spawning Agents

**Problem**: Who can spawn agents? With what permissions?

**Proposed Model**:
```
Agent Permissions Matrix:
┌─────────────────┬──────────┬────────────┬────────────┐
│ Role            │ Spawn    │ Max Steps  │ Tools      │
├─────────────────┼──────────┼────────────┼────────────┤
│ Admin           │ ✅ Any   │ Unlimited  │ All        │
│ Agent User      │ ✅ Own   │ 50         │ Safe+Moderate│
│ Viewer          │ ❌       │ -          │ -          │
└─────────────────┴──────────┴────────────┴────────────┘
```

**Implementation**:
- Add `agent_permissions` to User model
- Check permissions in `AgentService.spawn()`
- Log all spawns to audit trail

---

### Q3: Multi-LLM Orchestration (Simultaneous Backends)

**Problem**: We support Ollama/OpenAI/Groq, but only one at a time per request.

**Solution**: **LLM Router** - Choose the right model for the task.

| Strategy | How It Works | Use Case |
| :--- | :--- | :--- |
| **Task-Based** | Coding → Claude, Research → GPT-4, Quick → Groq | Optimize cost/quality |
| **Fallback Chain** | Try Ollama → if fail → OpenAI | Reliability |
| **Parallel Consensus** | Ask 3 LLMs, vote on answer | Critical decisions |
| **Cost Optimizer** | Easy tasks → local, Hard → cloud | Budget control |

**Implementation**:
```python
class LLMRouter:
    async def route(self, task_type: str, complexity: str) -> str:
        if task_type == "coding" and complexity == "high":
            return "claude-3-opus"
        elif task_type == "quick_answer":
            return "groq/llama-70b"  # Fast
        else:
            return "ollama/mistral"  # Local default
```

- Add `LLMRouter` service
- Extend `AgentConfig` with `llm_strategy`
- UI: Let users configure routing rules per agent


