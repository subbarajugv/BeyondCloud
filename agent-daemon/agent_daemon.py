#!/usr/bin/env python3
"""
BeyondCloud Local Agent Daemon

A lightweight local daemon that enables the AI to work with files on your machine.
Runs on localhost:8002 and only accepts connections from your browser.

Usage:
    python agent_daemon.py [--port 8002] [--sandbox /path/to/folder]

The daemon will:
- Listen on localhost only (not accessible from network)
- Execute file operations (read, write, list, search)
- Execute shell commands (with your approval)
- Provide tool schemas for LLM function calling
"""

import os
import sys
import uuid
import argparse
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Try to import FastAPI - if not available, provide helpful error
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install fastapi uvicorn pydantic")
    sys.exit(1)


# ========== Configuration ==========

DEFAULT_PORT = 8002
VERSION = "1.0.0"


# ========== Models ==========

class ApprovalMode(str, Enum):
    REQUIRE_APPROVAL = "require_approval"
    TRUST_MODE = "trust_mode"


class SetSandboxRequest(BaseModel):
    path: str


class SetModeRequest(BaseModel):
    mode: ApprovalMode


class ExecuteToolRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    approved: bool = False


class ToolCallPending(BaseModel):
    id: str
    tool_name: str
    args: Dict[str, Any]
    safety_level: str


# ========== Tool Schemas for LLM ==========

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the working directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the working directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the working directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in the working directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list (default: current directory)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to search for (e.g., '*.py', '**/*.ts')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory (default: current)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the working directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to execute"
                    }
                },
                "required": ["cmd"]
            }
        }
    }
]


# ========== Sandbox Security ==========

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "less", "more", "wc", "file",
    "find", "grep", "egrep", "fgrep", "awk", "sed",
    "tree", "du", "df", "stat", "pwd", "echo",
    "git", "python", "node", "npm", "pip",
}

DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "rmdir",
    "sudo", "su ",
    "> /dev", ">/dev",
    "chmod 777", "chmod -R",
    "curl", "wget", "nc ", "netcat",
    "eval", "exec",
    "$(", "`",
    "&&", "||", ";",
]


def classify_command(cmd: str) -> Tuple[str, str]:
    """Classify command safety level"""
    cmd_lower = cmd.lower().strip()
    
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return "dangerous", f"Contains dangerous pattern: {pattern}"
    
    cmd_base = cmd_lower.split()[0] if cmd_lower else ""
    if cmd_base in SAFE_COMMANDS:
        return "safe", "Known safe command"
    
    return "moderate", "Unknown command - requires approval"


class SandboxGuard:
    """Ensures all file operations stay within sandbox"""
    
    def __init__(self, sandbox_path: str):
        expanded = os.path.expanduser(sandbox_path)
        self.sandbox_path = Path(expanded).resolve()
        
        if not self.sandbox_path.exists():
            raise ValueError(f"Path does not exist: {sandbox_path}")
        if not self.sandbox_path.is_dir():
            raise ValueError(f"Not a directory: {sandbox_path}")
    
    def resolve_path(self, path: str) -> Path:
        """Resolve path within sandbox, raise if escapes"""
        if not path or path == ".":
            return self.sandbox_path
            
        if os.path.isabs(path):
            full_path = Path(path).resolve()
        else:
            full_path = (self.sandbox_path / path).resolve()
        
        try:
            full_path.relative_to(self.sandbox_path)
            return full_path
        except ValueError:
            raise PermissionError(f"Path escapes sandbox: {path}")


# ========== Agent Tools ==========

class AgentTools:
    """Local file and command operations"""
    
    def __init__(self, sandbox_path: str):
        self.guard = SandboxGuard(sandbox_path)
        self.sandbox_path = self.guard.sandbox_path
    
    def read_file(self, path: str) -> Dict[str, Any]:
        try:
            resolved = self.guard.resolve_path(path)
            if not resolved.exists():
                return {"error": f"File not found: {path}"}
            if not resolved.is_file():
                return {"error": f"Not a file: {path}"}
            
            content = resolved.read_text(encoding='utf-8', errors='replace')
            return {"content": content, "path": str(resolved), "size": len(content)}
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Read error: {e}"}
    
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        try:
            resolved = self.guard.resolve_path(path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding='utf-8')
            return {"success": True, "path": str(resolved), "bytes": len(content)}
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Write error: {e}"}
    
    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        try:
            resolved = self.guard.resolve_path(path)
            if not resolved.exists():
                return {"error": f"Directory not found: {path}"}
            if not resolved.is_dir():
                return {"error": f"Not a directory: {path}"}
            
            entries = []
            for item in sorted(resolved.iterdir()):
                entry = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_file():
                    entry["size"] = item.stat().st_size
                entries.append(entry)
            
            return {"entries": entries, "count": len(entries), "path": str(resolved)}
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"List error: {e}"}
    
    def search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        try:
            resolved = self.guard.resolve_path(path)
            matches = []
            
            for item in resolved.rglob(pattern):
                try:
                    rel_path = item.relative_to(self.sandbox_path)
                    matches.append({
                        "path": str(rel_path),
                        "type": "directory" if item.is_dir() else "file"
                    })
                except ValueError:
                    continue
                
                if len(matches) >= 100:
                    break
            
            return {"matches": matches, "count": len(matches), "pattern": pattern}
        except Exception as e:
            return {"error": f"Search error: {e}"}
    
    def run_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.sandbox_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": cmd
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "command": cmd}
        except Exception as e:
            return {"error": f"Command error: {e}", "command": cmd}


# ========== Daemon State ==========

@dataclass
class DaemonState:
    sandbox_path: Optional[str] = None
    approval_mode: ApprovalMode = ApprovalMode.REQUIRE_APPROVAL
    pending_calls: Dict[str, ToolCallPending] = field(default_factory=dict)
    tools: Optional[AgentTools] = None


state = DaemonState()


# ========== FastAPI App ==========

app = FastAPI(
    title="BeyondCloud Local Agent",
    version=VERSION,
    description="Local agent daemon for file operations and command execution"
)

# CORS - allow browser access from common frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",  # Common
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "BeyondCloud Local Agent",
        "version": VERSION,
        "status": "running",
        "sandbox_active": state.tools is not None,
        "sandbox_path": state.sandbox_path
    }


@app.get("/api/agent/status")
def get_status():
    return {
        "sandbox_path": state.sandbox_path,
        "sandbox_active": state.tools is not None,
        "approval_mode": state.approval_mode.value,
        "pending_approvals": len(state.pending_calls),
    }


@app.post("/api/agent/set-sandbox")
def set_sandbox(request: SetSandboxRequest):
    try:
        tools = AgentTools(request.path)
        state.sandbox_path = str(tools.sandbox_path)
        state.tools = tools
        return {
            "success": True,
            "sandbox_path": state.sandbox_path,
            "message": f"Working directory set to: {state.sandbox_path}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agent/set-mode")
def set_mode(request: SetModeRequest):
    state.approval_mode = request.mode
    return {
        "success": True,
        "mode": request.mode.value,
        "message": f"Approval mode set to: {request.mode.value}"
    }


@app.get("/api/agent/tools")
def get_tools():
    return {"tools": TOOL_SCHEMAS}


@app.post("/api/agent/execute")
def execute_tool(request: ExecuteToolRequest):
    if state.tools is None:
        raise HTTPException(status_code=400, detail="Working directory not set")
    
    tool_name = request.tool_name
    args = request.args
    
    # Determine if approval needed
    needs_approval = True
    safety_level = "moderate"
    
    if tool_name == "run_command":
        safety_level, _ = classify_command(args.get("cmd", ""))
    
    if state.approval_mode == ApprovalMode.TRUST_MODE:
        if tool_name != "run_command":
            needs_approval = False
    
    # If not approved, queue for approval
    if needs_approval and not request.approved:
        call_id = str(uuid.uuid4())
        pending = ToolCallPending(
            id=call_id,
            tool_name=tool_name,
            args=args,
            safety_level=safety_level
        )
        state.pending_calls[call_id] = pending
        
        return {
            "status": "pending_approval",
            "call_id": call_id,
            "tool_name": tool_name,
            "args": args,
            "safety_level": safety_level,
            "message": "Tool call requires approval"
        }
    
    # Execute the tool
    tools = state.tools
    
    if tool_name == "read_file":
        result = tools.read_file(args.get("path", ""))
    elif tool_name == "write_file":
        result = tools.write_file(args.get("path", ""), args.get("content", ""))
    elif tool_name == "list_dir":
        result = tools.list_dir(args.get("path", "."))
    elif tool_name == "search_files":
        result = tools.search_files(args.get("pattern", "*"), args.get("path", "."))
    elif tool_name == "run_command":
        result = tools.run_command(args.get("cmd", ""))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    
    return {
        "status": "error" if "error" in result else "success",
        "tool_name": tool_name,
        "args": args,
        "result": result,
        "error": result.get("error")
    }


@app.post("/api/agent/approve/{call_id}")
def approve_call(call_id: str):
    if call_id not in state.pending_calls:
        raise HTTPException(status_code=404, detail="Pending call not found")
    
    pending = state.pending_calls.pop(call_id)
    return execute_tool(ExecuteToolRequest(
        tool_name=pending.tool_name,
        args=pending.args,
        approved=True
    ))


@app.post("/api/agent/reject/{call_id}")
def reject_call(call_id: str):
    if call_id not in state.pending_calls:
        raise HTTPException(status_code=404, detail="Pending call not found")
    
    pending = state.pending_calls.pop(call_id)
    return {
        "status": "rejected",
        "tool_name": pending.tool_name,
        "message": "Tool call rejected by user"
    }


@app.get("/api/agent/pending")
def get_pending_calls():
    return {
        "pending": [
            {
                "id": p.id,
                "tool_name": p.tool_name,
                "args": p.args,
                "safety_level": p.safety_level,
            }
            for p in state.pending_calls.values()
        ]
    }


# ========== CLI Entry Point ==========

def main():
    parser = argparse.ArgumentParser(
        description="BeyondCloud Local Agent Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent_daemon.py                    # Start on default port 8002
  python agent_daemon.py --port 9000        # Start on custom port
  python agent_daemon.py --sandbox ~/code   # Start with pre-set working directory
        """
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--sandbox", "-s",
        type=str,
        help="Pre-set working directory"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"BeyondCloud Local Agent v{VERSION}"
    )
    
    args = parser.parse_args()
    
    # Pre-set sandbox if provided
    if args.sandbox:
        try:
            tools = AgentTools(args.sandbox)
            state.sandbox_path = str(tools.sandbox_path)
            state.tools = tools
            print(f"Working directory: {state.sandbox_path}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           BeyondCloud Local Agent v{VERSION}                   ║
╠══════════════════════════════════════════════════════════════╣
║  Running on: http://localhost:{args.port}                        ║
║  Status:     http://localhost:{args.port}/api/agent/status       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if not state.sandbox_path:
        print("⚠️  No working directory set. Configure in the web UI.")
    
    print("Press Ctrl+C to stop.\n")
    
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
