# BeyondCloud Local Agent Daemon

A lightweight daemon that runs on your machine to enable AI file and command operations.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the daemon
python agent_daemon.py

# Or with a preset working directory
python agent_daemon.py --sandbox ~/projects/myapp
```

## Usage

1. Start the daemon on your machine
2. Open the BeyondCloud web app
3. Go to Settings → Agent → Select "Local Agent" mode
4. Set your working directory in the UI
5. Start chatting - the AI can now work with your files!

## API Endpoints

- `GET /` - Daemon status
- `GET /api/agent/status` - Agent status
- `POST /api/agent/set-sandbox` - Set working directory
- `GET /api/agent/tools` - Get tool schemas
- `POST /api/agent/execute` - Execute a tool
- `POST /api/agent/approve/{id}` - Approve pending tool
- `POST /api/agent/reject/{id}` - Reject pending tool

## Security

- Runs on localhost only (127.0.0.1)
- CORS restricted to known frontend origins
- Commands require approval by default
- All file operations sandboxed to working directory
