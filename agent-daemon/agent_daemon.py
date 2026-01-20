#!/usr/bin/env python3
"""
BeyondCloud Agent Daemon

A lightweight agent daemon that provides HTTP API + approval flow.
Delegates all tool execution to BeyondCloudToolsServer (MCP).

Same daemon works locally or in cloud - just needs MCP server.
"""

import os
import sys
import uuid
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add parent dir to path for mcp_servers import
sys.path.insert(0, str(Path(__file__).parent.parent / "backend-python"))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install fastapi uvicorn pydantic")
    sys.exit(1)

# Import MCP server (single source of truth for tools)
try:
    from mcp_servers.beyondcloud_tools import BeyondCloudToolsServer
except ImportError:
    print("Cannot import MCP server. Ensure backend-python is in path.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-daemon")

# ========== Configuration ==========

DEFAULT_PORT = 8002
VERSION = "3.0.0"

# CORS - configurable via env
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else DEFAULT_CORS_ORIGINS

# ========== API Models ==========

class ApprovalMode(str, Enum):
    REQUIRE_APPROVAL = "require_approval"
    TRUST_MODE = "trust_mode"

class SetSandboxRequest(BaseModel):
    path: str

class SetModeRequest(BaseModel):
    mode: ApprovalMode

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]
    approved: bool = False

class ToolCallPending(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]
    safety_level: str

# ========== Daemon State ==========

@dataclass
class DaemonState:
    sandbox_path: Optional[str] = None
    approval_mode: ApprovalMode = ApprovalMode.REQUIRE_APPROVAL
    pending_calls: Dict[str, ToolCallPending] = field(default_factory=dict)
    mcp_server: Optional[BeyondCloudToolsServer] = None

state = DaemonState()

# ========== Security ==========

DANGEROUS_PATTERNS = ["rm -rf", "sudo", "chmod 777", "curl", "wget", "eval", "exec"]
SAFE_COMMANDS = {"ls", "cat", "head", "tail", "find", "grep", "git", "python", "node"}

def classify_command(cmd: str) -> str:
    cmd_lower = cmd.lower()
    for p in DANGEROUS_PATTERNS:
        if p in cmd_lower:
            return "dangerous"
    if cmd_lower.split()[0] in SAFE_COMMANDS if cmd_lower else False:
        return "safe"
    return "moderate"

# ========== FastAPI App ==========

app = FastAPI(title="BeyondCloud Agent Daemon", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": "BeyondCloud Agent Daemon",
        "version": VERSION,
        "status": "running",
        "sandbox": state.sandbox_path,
        "mcp_active": state.mcp_server is not None
    }

@app.get("/api/agent/status")
def get_status():
    return {
        "sandbox_path": state.sandbox_path,
        "sandbox_active": state.mcp_server is not None,
        "approval_mode": state.approval_mode.value,
        "pending_count": len(state.pending_calls)
    }

@app.post("/api/agent/set-sandbox")
def set_sandbox(request: SetSandboxRequest):
    try:
        # Create MCP server with sandbox path
        state.mcp_server = BeyondCloudToolsServer(sandbox_path=request.path)
        state.sandbox_path = request.path
        return {"success": True, "path": state.sandbox_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/agent/set-mode")
def set_mode(request: SetModeRequest):
    state.approval_mode = request.mode
    return {"success": True, "mode": request.mode.value}

# ========== MCP Endpoints ==========

@app.get("/api/mcp/tools")
async def list_tools():
    if not state.mcp_server:
        raise HTTPException(status_code=400, detail="Sandbox not set")
    result = await state.mcp_server._handle_tools_list()
    return result

@app.post("/api/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    if not state.mcp_server:
        raise HTTPException(status_code=400, detail="Sandbox not set")
    
    # Check safety for commands
    safety = "moderate"
    if request.name == "run_command":
        safety = classify_command(request.arguments.get("cmd", ""))
    
    # Approval check
    if not request.approved and state.approval_mode == ApprovalMode.REQUIRE_APPROVAL:
        if request.name not in ["think", "plan_task"]:  # Auto-approve planning tools
            call_id = str(uuid.uuid4())
            state.pending_calls[call_id] = ToolCallPending(
                id=call_id, name=request.name, 
                arguments=request.arguments, safety_level=safety
            )
            return {"status": "pending_approval", "call_id": call_id, "tool_name": request.name, "safety_level": safety}
    
    # Execute via MCP server
    result = await state.mcp_server._execute_tool(request.name, request.arguments)
    return {
        "status": "error" if result.isError else "success",
        "content": [asdict(c) if hasattr(c, '__dict__') else c for c in result.content]
    }

# ========== Approval Flow ==========

@app.get("/api/agent/pending")
def get_pending():
    return {"pending": list(state.pending_calls.values())}

@app.post("/api/agent/approve/{call_id}")
async def approve_call(call_id: str):
    if call_id not in state.pending_calls:
        raise HTTPException(status_code=404, detail="Not found")
    pending = state.pending_calls.pop(call_id)
    return await call_tool(ToolCallRequest(name=pending.name, arguments=pending.arguments, approved=True))

@app.post("/api/agent/reject/{call_id}")
def reject_call(call_id: str):
    if call_id not in state.pending_calls:
        raise HTTPException(status_code=404, detail="Not found")
    state.pending_calls.pop(call_id)
    return {"status": "rejected"}

# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(description="BeyondCloud Agent Daemon")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sandbox", "-s", type=str)
    args = parser.parse_args()

    if args.sandbox:
        try:
            state.mcp_server = BeyondCloudToolsServer(sandbox_path=args.sandbox)
            state.sandbox_path = args.sandbox
            logger.info(f"Sandbox: {args.sandbox}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    print(f"🚀 Agent Daemon v{VERSION} on port {args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
