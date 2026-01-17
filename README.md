# BeyondCloud multi-tenant multi-user chat interface

A multi-user web interface for llama.cpp, ollama, cloud models with user authentication and login functionality.

## Project Structure

```
BeyondCloud-webui/
├── frontend/              # Svelte 5 WebUI (copied from llama.cpp)
├── backend-python/        # Python/FastAPI - AI Service (RAG, Agents, MCP)
├── backend-nodejs/        # Node.js/Express - Core API (Auth, Chat)
├── docs/                  # Documentation
│   ├── task.md            # Development roadmap
│   ├── api-contract.md    # Complete API specification
│   └── AGENT_CONTRACT.md  # Agent tool contracts
└── README.md
```

## Backend Architecture

The backends serve **different purposes** in the architecture:

| | Node.js/Express | Python/FastAPI |
|--|-----------------|----------------|
| **Role** | Core API Gateway | AI Service |
| **Features** | Auth, Chat, Conversations | RAG, Agents, MCP, Tracing |
| **Port** | 3000 | 8000 |
| **Required** | Yes | For AI features |

**Minimal setup**: Frontend + Node.js backend
**Full setup**: Frontend + Node.js backend + Python AI service

## Features

### ✅ Implemented
- **User Authentication**: JWT-based login/register with refresh tokens
- **Multi-User Support**: Isolated conversations per user
- **PostgreSQL Storage**: Conversations, messages, settings
- **RBAC**: Role-based access control (user, rag_user, agent_user, admin, owner)
- **RAG System**: Document ingestion, vector search, hybrid retrieval
- **Agent Tools**: File operations, command execution with approval UI
- **MCP Integration**: External tool servers (filesystem, GitHub, etc.)
- **Tracing**: OpenTelemetry-compatible observability

### 🚧 In Progress
- RAG Advanced: User-configurable chunking, reranking, grounding options

## Quick Start

### Prerequisites

- Node.js 18+ (frontend + Node backend)
- Python 3.11+ (AI features)
- PostgreSQL database
- llama.cpp server or Ollama running

### 1. Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

### 2. Node.js Backend (Required)

```bash
cd backend-nodejs
npm install
cp .env.example .env   # Configure DATABASE_URL, JWT_SECRET
npm run dev            # http://localhost:3000
```

### 3. Python AI Service (For RAG/Agents)

```bash
cd backend-python
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
python main.py         # http://localhost:8000
```

## Development Phases

| Phase | Component | Status |
|-------|-----------|--------|
| 0 | Multi-Backend LLM | ✅ Done |
| 1 | Backend (Auth, DB) | ✅ Done |
| 2 | Frontend (Auth UI) | ✅ Done |
| 3 | Data Migration | ✅ Done |
| 4 | RAG & Tracing | ✅ Done |
| 5 | Agents & Tools | ✅ Done |
| 6 | MCP Integration | ✅ Done |
| 7 | RAG Advanced | 🚧 Next |
| 8 | Agents Advanced | To Do |
| 9 | Security (RBAC) | ✅ Done |

## Configuration

**Frontend** (`.env`):
```env
PUBLIC_API_URL=http://localhost:3000/api
```

**Node.js Backend** (`.env`):
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/beyondcloud
JWT_SECRET=your-secret-key
LLAMA_CPP_URL=http://localhost:8080
```

**Python Backend** (`.env`):
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/beyondcloud
DEFAULT_LLM_PROVIDER=llama.cpp
LLAMA_CPP_BASE_URL=http://localhost:8080/v1
```

## Documentation

- [API Contract](docs/api-contract.md) - Complete API specification
- [Task Roadmap](docs/task.md) - Development phases and status
- [Agent Contract](docs/AGENT_CONTRACT.md) - Agent tool specifications

## License

MIT License (same as llama.cpp)

## Credits

- **llama.cpp** - Original project by ggml-org
- **WebUI** - Original Svelte WebUI from llama.cpp project
