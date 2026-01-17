# BeyondCloud multi-tenant multi-user chat interface

A multi-user web interface for llama.cpp, ollama, cloud models with user authentication and login functionality.

## Project Structure

```
BeyondCloud-webui/
├── frontend/              # Svelte 5 WebUI (copied from llama.cpp)
├── backend-python/        # Python/FastAPI implementation
├── backend-nodejs/        # Node.js/Express implementation
├── docs/                  # Documentation
│   ├── implementation_plan.md
│   ├── api-contract.md    # Complete API specification
│   └── component-architecture.md
└── README.md
```

## Choose Your Backend

Both backends implement the **exact same API**. Pick based on your team's expertise:

| | Python/FastAPI | Node.js/Express |
|--|----------------|-----------------|
| **Status** | ✅ Implemented | ✅ Implemented |
| **Best for** | Python teams, ML/AI, RAG | JS/TS teams |
| **Features** | Auth, Chat, RAG, Agents | Auth, Chat |
| **Folder** | `backend-python/` | `backend-nodejs/` |

## Features

- ✅ **User Authentication**: JWT-based login/register system
- ✅ **Multi-User Support**: Each user has isolated conversations
- ✅ **Server-Side Storage**: Conversations stored in PostgreSQL
- ✅ **Secure**: Password hashing, JWT tokens, CORS protection
- ✅ **Modern UI**: Svelte 5 + TailwindCSS v4
- ✅ **RAG Support**: Document ingestion and retrieval (Python backend)
- ✅ **Agent Tools**: Sandboxed file operations and command execution (Python backend)

## Quick Start

### Prerequisites

- Node.js 18+ (for frontend)
- Python 3.11+ or Node.js 18+ (for backend - choose one)
- PostgreSQL database
- llama.cpp server or Ollama running

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup (Python - Recommended)

```bash
cd backend-python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Backend Setup (Node.js)

```bash
cd backend-nodejs
npm install
npm run dev
```

See each backend's `README.md` for detailed configuration and setup instructions.

## Documentation

- **[API Contract](docs/api-contract.md)** - Complete API specification
- **[Implementation Plan](docs/implementation_plan.md)** - Architecture and design guide
- **[Component Architecture](docs/component-architecture.md)** - Frontend component design
- See `backend-python/docs/` and `backend-nodejs/docs/` for backend-specific docs

## Development Status

### ✅ Phase 1: Backend Setup - Complete
- [x] Python/FastAPI backend implemented
- [x] Node.js/Express backend implemented
- [x] PostgreSQL database integration
- [x] Authentication endpoints (login, register, refresh)
- [x] Conversation/message APIs
- [x] LLM proxy endpoints (llama.cpp, Ollama)

### ✅ Phase 2: Frontend Authentication - Complete
- [x] Auth store with JWT handling
- [x] Login/register pages
- [x] Route protection
- [x] JWT token refresh
- [x] User menu with logout

### ✅ Phase 3: Data Migration - Complete
- [x] API-backed data persistence
- [x] Chat store integration
- [x] Settings store integration

### ✅ Phase 4: Advanced Features - Complete
- [x] RAG system (document ingestion, retrieval, embedding)
- [x] Agent tools (file operations, command execution)
- [x] Tool approval UI for agent actions
- [x] Sandbox settings configuration

## Configuration

### Environment Variables

**Frontend** (`.env`):
```env
PUBLIC_API_URL=http://localhost:3000/api
```

**Backend** (`.env`):
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/llamacpp_chat
JWT_SECRET=your-secret-key-here
JWT_EXPIRY=24h
LLAMA_CPP_URL=http://localhost:8080
PORT=3000
```

## Contributing

This project is based on the llama.cpp WebUI. See the implementation plan for contribution guidelines.

## License

Same as llama.cpp - MIT License

## Credits

- **llama.cpp** - Original project by ggml-org
- **WebUI** - Original Svelte WebUI from llama.cpp project
- **Authentication Layer** - Custom implementation for multi-user support
