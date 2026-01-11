# Documentation Index

All planning and implementation documents for the llama.cpp Authenticated WebUI project.

## Quick Start

1. Read [implementation_plan.md](implementation_plan.md) - Full plan with all phases
2. Review [api-contract.md](api-contract.md) - API specification for development
3. Choose your backend in [component-architecture.md](component-architecture.md)

## Documents

| Document | Purpose |
|----------|---------|
| [implementation_plan.md](implementation_plan.md) | Main implementation plan with 8 phases |
| [CONTRACT.md](CONTRACT.md) | **Formal API contract** (inputs, outputs, guarantees, failures) |
| [AGENT_CONTRACT.md](AGENT_CONTRACT.md) | **Agent sub-contracts** (9 contracts + RAG add-on) |
| [api-contract.md](api-contract.md) | Complete API specification (enables parallel dev) |
| [component-architecture.md](component-architecture.md) | Component diagram, dual backend options |
| [multi-backend-pros-cons.md](multi-backend-pros-cons.md) | LLM provider analysis |
| [task.md](task.md) | Task checklist and progress tracking |
| [webui-info.md](webui-info.md) | Original WebUI analysis notes |

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Multi-Backend LLM Integration | To Do |
| 1 | Backend (Auth, DB, APIs) | To Do |
| 2 | Frontend (Auth UI) - *can parallel with 1* | To Do |
| 3 | Data Migration | To Do |
| 4 | Testing & Polish | To Do |
| 5 | Production Deployment | To Do |
| 6 | MCP Integration | Placeholder |

## Backend Choices

| Python | Node.js |
|--------|---------|
| `backend-python/` | `backend-nodejs/` |
| FastAPI | Express |
| SQLAlchemy | TypeORM |
| Same API! | Same API! |
