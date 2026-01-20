# BeyondCloud Agent

AI-powered coding assistant with local or cloud LLM support and tool execution.

## Installation

```bash
# Install from source
cd agent-daemon
pip install -e .
```

## Usage

### CLI Mode (New!)

```bash
# Run with local Ollama
beyondcloud "Create a Python script that lists files"

# Run with llama.cpp
beyondcloud "Explain this code" --llm http://localhost:8080/v1

# Interactive mode
beyondcloud -i

# With OpenAI API
beyondcloud "Refactor this" --llm https://api.openai.com/v1 --api-key $OPENAI_API_KEY
```

### Daemon Mode

```bash
# Start the daemon (for web UI integration)
python agent_daemon.py --sandbox ~/projects/myapp
```

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `BEYONDCLOUD_LLM_URL` | `http://localhost:11434/v1` | LLM endpoint |
| `BEYONDCLOUD_MODEL` | `qwen2.5-coder:7b` | Model name |
| `BEYONDCLOUD_MCP_URL` | `http://localhost:8001/api/mcp` | MCP tools server |

## Architecture

```
CLI/Daemon → Agent Core → LLM (local/cloud) → MCP Tools → Sandbox
```

- **Agent Core** (`agent.py`): Agentic loop with tool calling
- **CLI** (`cli.py`): Command-line interface
- **Daemon** (`agent_daemon.py`): HTTP server for web UI integration

## API Endpoints (Daemon Mode)

- `GET /` - Status
- `GET /api/agent/tools` - Available tools
- `POST /api/agent/execute` - Execute a tool
- `POST /api/agent/approve/{id}` - Approve pending tool

## Security

- Runs on localhost only
- Commands require approval
- File operations sandboxed to working directory
