# BeyondCloud

Multi-user LLM chat interface with RAG, Agents, and MCP integration.

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ 
- **Python** 3.11+ with `uv` package manager
- **PostgreSQL** 15+ with pgvector extension
- **LLM Server**: llama.cpp, Ollama, or cloud API

### Installation

```bash
# 1. Clone and setup
git clone https://github.com/subbarajugv/BeyondCloud.git
cd BeyondCloud

# 2. Frontend
cd frontend && npm install

# 3. Node.js Backend
cd ../backend-nodejs && npm install
cp .env.example .env  # Edit with your settings

# 4. Python Backend
cd ../backend-python
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
```

### Run All Services

```bash
# Terminal 1: Frontend (http://localhost:5173)
cd frontend && npm run dev

# Terminal 2: Node.js Backend (http://localhost:3000)
cd backend-nodejs && npm run dev

# Terminal 3: Python Backend (http://localhost:8001)
cd backend-python && source .venv/bin/activate && python main.py
```

---

## 📁 Project Structure

```
BeyondCloud/
├── frontend/           # Svelte 5 WebUI
├── backend-nodejs/     # Auth, Conversations, Settings
├── backend-python/     # RAG, Agents, MCP, Analytics
└── docs/               # API Contracts
```

---

## ⚙️ Configuration

### Node.js Backend (`.env`)

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/beyondcloud
JWT_SECRET=your-secret-key
LLAMA_CPP_URL=http://localhost:8080
PORT=3000
```

### Python Backend (`.env`)

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/beyondcloud
PORT=8001
DEFAULT_LLM_PROVIDER=llama.cpp
LLAMA_CPP_BASE_URL=http://localhost:8080/v1

# Storage (local by default)
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=./storage

# For S3 (production)
# STORAGE_TYPE=s3
# S3_BUCKET=your-bucket
# S3_ENDPOINT=https://your-endpoint.com
# S3_ACCESS_KEY=your-key
# S3_SECRET_KEY=your-secret
```

---

## 📚 RAG (Knowledge Base)

### Upload Documents

1. Open the **Knowledge Library** panel (sidebar)
2. Click **Upload** → drag files or paste text
3. Configure chunk size/overlap if needed
4. Click **Upload**

### Query Your Documents

1. Enable RAG toggle (📚 icon in chat input)
2. Ask questions - responses will be grounded in your documents
3. View citations in the response

### RAG Settings

Open **Settings → RAG** to configure:
- Chunk size and overlap
- Hybrid search (BM25 + vector)
- Reranking options
- Context assembly
- Citation requirements

### Supported Formats

- `.txt`, `.md`, `.pdf`, `.docx`, `.html`

---

## 🤖 Agent Tools

### Enable Agents

1. Open **Settings → Agent**
2. Set sandbox path (e.g., `/home/user/projects`)
3. Enable tools you want to allow

### Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write to file (requires approval) |
| `list_dir` | List directory contents |
| `search_files` | Search files by pattern |
| `execute_command` | Run shell command (requires approval) |

### Approval Flow

Dangerous actions (write, execute) require explicit approval:
1. Agent proposes action
2. UI shows approval dialog
3. User approves/rejects
4. Action executes if approved

---

## 🔌 MCP (Model Context Protocol)

### Add MCP Server

1. Open **Settings → Agent → MCP Servers**
2. Add server (e.g., `npx @modelcontextprotocol/server-filesystem`)
3. Tools become available to the agent

### Example MCP Servers

```bash
# Filesystem access
npx @modelcontextprotocol/server-filesystem /path/to/dir

# GitHub integration
npx @modelcontextprotocol/server-github --token YOUR_TOKEN
```

---

## 🔐 Roles & Permissions

| Role | Capabilities |
|------|--------------|
| `user` | Chat only |
| `rag_user` | Chat + RAG |
| `agent_user` | Chat + RAG + Agents |
| `admin` | All + user management |

---

## 📡 API Endpoints

| Service | Port | Key Routes |
|---------|------|------------|
| Node.js | 3000 | `/api/auth/*`, `/api/conversations/*` |
| Python | 8001 | `/api/rag/*`, `/api/agent/*`, `/api/mcp/*` |

See [docs/API_OVERVIEW.md](docs/API_OVERVIEW.md) for full endpoint list.

---

## 📖 Documentation

- [API Overview](docs/API_OVERVIEW.md) - All endpoints
- [Core Contract](docs/CONTRACT.md) - Protocol standards
- [RAG Contract](docs/RAG_CONTRACT.md) - RAG pipeline
- [Agent Contract](docs/AGENT_CONTRACT.md) - Agent tools
- [Database Schema](docs/DATABASE_SCHEMA.md) - ER diagram

---

## 🛠️ Development

```bash
# Type check frontend
cd frontend && npm run check

# Run Python tests
cd backend-python && pytest

# Format code
npm run format  # frontend
uv run black .  # python
```

---

## License

MIT License (same as llama.cpp)
