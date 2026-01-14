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
| **Best for** | Python teams, ML/AI | JS/TS teams |
| **Quick Start** | `pip install` | `npm install` |
| **Folder** | `backend-python/` | `backend-nodejs/` |

## Features

- ✅ **User Authentication**: JWT-based login/register system
- ✅ **Multi-User Support**: Each user has isolated conversations
- ✅ **Server-Side Storage**: Conversations stored in database (PostgreSQL/MySQL)
- ✅ **Secure**: Password hashing, JWT tokens, CORS protection
- ✅ **Modern UI**: Svelte 5 + TailwindCSS v4

## Quick Start

### Prerequisites

- Node.js 18+ (for frontend)
- Backend runtime (Node.js/Python/Go - choose one)
- PostgreSQL or MySQL database
- llama.cpp server running

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

**Coming soon** - Choose your backend technology:
- Node.js + Express
- Python + FastAPI  
- Go

See `docs/implementation_plan.md` for detailed setup instructions.

## Documentation

- **[Implementation Plan](docs/implementation_plan.md)** - Complete guide for adding authentication
- **Architecture** - See implementation plan for detailed architecture
- **API Documentation** - See implementation plan for API endpoints

## Development Roadmap

### Phase 1: Backend Setup ⏳
- [ ] Choose backend technology
- [ ] Set up database
- [ ] Implement authentication endpoints
- [ ] Implement conversation/message APIs
- [ ] Add llama.cpp proxy endpoint

### Phase 2: Frontend Authentication ⏳
- [ ] Create auth store
- [ ] Build login/register pages
- [ ] Add route protection
- [ ] Implement JWT token refresh
- [ ] Add user profile component

### Phase 3: Data Migration ⏳
- [ ] Replace IndexedDB with API calls
- [ ] Update chat store
- [ ] Update settings store
- [ ] Remove Dexie dependency

### Phase 4: Testing & Polish ⏳
- [ ] Test authentication flow
- [ ] Test multi-user isolation
- [ ] Add loading states
- [ ] Add error handling
- [ ] Implement session persistence

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
