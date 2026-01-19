#!/usr/bin/env python3
"""
BeyondCloud Local Agent Daemon (MCP Unified Version)

A lightweight local daemon that enables the AI to work with files on your machine.
Runs on localhost:8002 and only accepts connections from your browser.

Unifies local tool capabilities with the BeyondCloud MCP architecture.
"""

import os
import sys
import uuid
import argparse
import subprocess
import json
import asyncio
import logging
import base64
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Try to import FastAPI - if not available, provide helpful error
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install fastapi uvicorn pydantic duckduckgo-search playwright")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent-daemon")

# ========== Configuration ==========

DEFAULT_PORT = 8002
VERSION = "2.0.0"

# ========== MCP Models ==========

@dataclass
class Tool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class ToolResult:
    """Result from tool execution"""
    content: List[Dict[str, Any]]
    isError: bool = False

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

# ========== Sandbox Security Logic ==========

DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "rmdir", "sudo", "su ", "> /dev", ">/dev",
    "chmod 777", "chmod -R", "curl", "wget", "nc ", "netcat",
    "eval", "exec", "$(", "`", "&&", "||", ";"
]

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "file", "find", "grep", 
    "tree", "du", "df", "stat", "pwd", "echo", "git", "python", 
    "node", "npm", "pip"
}

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
        if not self.sandbox_path.exists() or not self.sandbox_path.is_dir():
            raise ValueError(f"Invalid sandbox directory: {sandbox_path}")

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

# ========== MCP Tool Implementation Class ==========

class BeyondCloudLocalMCP:
    """Local implementation of the unified MCP tools"""
    def __init__(self, sandbox_path: str):
        self.guard = SandboxGuard(sandbox_path)
        self.sandbox_path = self.guard.sandbox_path
        self._tools = self._register_tools()

    def _register_tools(self) -> Dict[str, Tool]:
        return {
            "web_search": Tool(name="web_search", description="Search the web (DuckDuckGo)", 
                               inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "num_results": {"type": "integer", "default": 5}}, "required": ["query"]}),
            "screenshot": Tool(name="screenshot", description="Capture webpage screenshot", 
                               inputSchema={"type": "object", "properties": {"url": {"type": "string"}, "full_page": {"type": "boolean", "default": False}}, "required": ["url"]}),
            "python_executor": Tool(name="python_executor", description="Execute sandboxed Python code", 
                                    inputSchema={"type": "object", "properties": {"code": {"type": "string"}, "timeout": {"type": "integer", "default": 10}}, "required": ["code"]}),
            "database_query": Tool(name="database_query", description="Execute read-only SQL query", 
                                   inputSchema={"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}),
            "read_file": Tool(name="read_file", description="Read file from sandbox", 
                             inputSchema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
            "write_file": Tool(name="write_file", description="Write file to sandbox", 
                              inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
            "list_dir": Tool(name="list_dir", description="List directory contents", 
                            inputSchema={"type": "object", "properties": {"path": {"type": "string", "default": "."}}, "required": []}),
            "search_files": Tool(name="search_files", description="Search files by pattern", 
                                inputSchema={"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}, "required": ["pattern"]}),
            "run_command": Tool(name="run_command", description="Run shell command in sandbox", 
                               inputSchema={"type": "object", "properties": {"cmd": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, "required": ["cmd"]}),
            "think": Tool(name="think", description="Record reasoning step", 
                         inputSchema={"type": "object", "properties": {"thought": {"type": "string"}}, "required": ["thought"]}),
            "plan_task": Tool(name="plan_task", description="Create execution plan", 
                             inputSchema={"type": "object", "properties": {"goal": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}}}, "required": ["goal", "steps"]}),
        }

    async def execute(self, name: str, args: Dict[str, Any]) -> ToolResult:
        method = f"_tool_{name}"
        if hasattr(self, method):
            try:
                return await getattr(self, method)(args)
            except Exception as e:
                logger.exception(f"Tool {name} failed: {e}")
                return ToolResult(content=[{"type": "text", "text": f"Error: {str(e)}"}], isError=True)
        return ToolResult(content=[{"type": "text", "text": f"Unknown tool: {name}"}], isError=True)

    # Implementations
    async def _tool_read_file(self, args):
        path = self.guard.resolve_path(args.get("path"))
        return ToolResult(content=[{"type": "text", "text": path.read_text(encoding='utf-8', errors='replace')}])

    async def _tool_write_file(self, args):
        path = self.guard.resolve_path(args.get("path"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content"), encoding='utf-8')
        return ToolResult(content=[{"type": "text", "text": f"Success: {path}"}])

    async def _tool_list_dir(self, args):
        path = self.guard.resolve_path(args.get("path", "."))
        entries = [{"name": i.name, "type": "dir" if i.is_dir() else "file"} for i in sorted(path.iterdir())]
        return ToolResult(content=[{"type": "text", "text": json.dumps(entries, indent=2)}])

    async def _tool_search_files(self, args):
        path = self.guard.resolve_path(args.get("path", "."))
        matches = [{"path": str(i.relative_to(self.sandbox_path)), "type": "dir" if i.is_dir() else "file"} 
                   for i in path.rglob(args.get("pattern"))][:100]
        return ToolResult(content=[{"type": "text", "text": json.dumps(matches, indent=2)}])

    async def _tool_run_command(self, args):
        cmd = args.get("cmd")
        safety, reason = classify_command(cmd)
        if safety == "dangerous": raise PermissionError(f"Blocked: {reason}")
        res = subprocess.run(cmd, shell=True, cwd=str(self.sandbox_path), capture_output=True, text=True, timeout=args.get("timeout", 30))
        out = res.stdout + (f"\n[stderr]: {res.stderr}" if res.stderr else "")
        return ToolResult(content=[{"type": "text", "text": out or "(no output)"}])

    async def _tool_web_search(self, args):
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(args.get("query"), max_results=args.get("num_results", 5)))
        formatted = [f"**{r.get('title')}**\n{r.get('href')}\n{r.get('body')}" for r in results]
        return ToolResult(content=[{"type": "text", "text": "\n\n".join(formatted)}])

    async def _tool_screenshot(self, args):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(args.get("url"), timeout=30000)
            img = await page.screenshot(full_page=args.get("full_page", False))
            await browser.close()
        return ToolResult(content=[{"type": "image", "data": base64.b64encode(img).decode("utf-8"), "mimeType": "image/png"}])

    async def _tool_python_executor(self, args):
        code = args.get("code")
        for b in ["os", "sys", "subprocess"]:
            if f"import {b}" in code or f"from {b}" in code: raise PermissionError(f"Blocked: {b}")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            path = f.name
        try:
            res = subprocess.run(['python', path], capture_output=True, text=True, timeout=args.get("timeout", 10))
            return ToolResult(content=[{"type": "text", "text": res.stdout + res.stderr or "(no output)"}])
        finally: os.unlink(path)

    async def _tool_database_query(self, args):
        return ToolResult(content=[{"type": "text", "text": "Database query not available in local daemon mode."}], isError=True)

    async def _tool_think(self, args):
        return ToolResult(content=[{"type": "text", "text": f"Thought recorded: {args.get('thought')}"}])

    async def _tool_plan_task(self, args):
        plan = f"Plan: {args.get('goal')}\n" + "\n".join([f"- {s}" for s in args.get("steps", [])])
        return ToolResult(content=[{"type": "text", "text": plan}])

# ========== Daemon State ==========

@dataclass
class DaemonState:
    sandbox_path: Optional[str] = None
    approval_mode: ApprovalMode = ApprovalMode.REQUIRE_APPROVAL
    pending_calls: Dict[str, ToolCallPending] = field(default_factory=dict)
    mcp: Optional[BeyondCloudLocalMCP] = None

state = DaemonState()

# ========== FastAPI App ==========

app = FastAPI(title="BeyondCloud Local Agent (MCP)", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"name": "BeyondCloud Local Agent", "version": VERSION, "status": "running", "sandbox": state.sandbox_path}

@app.get("/api/agent/status")
def get_status():
    return {"sandbox_path": state.sandbox_path, "sandbox_active": state.mcp is not None, "approval_mode": state.approval_mode.value, "pending_count": len(state.pending_calls)}

@app.post("/api/agent/set-sandbox")
def set_sandbox(request: SetSandboxRequest):
    try:
        state.mcp = BeyondCloudLocalMCP(request.path)
        state.sandbox_path = str(state.mcp.sandbox_path)
        return {"success": True, "path": state.sandbox_path}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/agent/set-mode")
def set_mode(request: SetModeRequest):
    state.approval_mode = request.mode
    return {"success": True, "mode": request.mode.value}

# --- MCP Compatible Endpoints ---

@app.get("/api/mcp/tools")
def list_tools():
    if not state.mcp: raise HTTPException(status_code=400, detail="Sandbox not set")
    return {"tools": [asdict(t) for t in state.mcp._tools.values()]}

@app.post("/api/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    if not state.mcp: raise HTTPException(status_code=400, detail="Sandbox not set")
    
    safety = "moderate"
    if request.name == "run_command":
        safety, _ = classify_command(request.arguments.get("cmd", ""))
    
    if not request.approved and state.approval_mode == ApprovalMode.REQUIRE_APPROVAL:
        if request.name not in ["think", "plan_task"]:
            call_id = str(uuid.uuid4())
            state.pending_calls[call_id] = ToolCallPending(id=call_id, name=request.name, arguments=request.arguments, safety_level=safety)
            return {"status": "pending_approval", "call_id": call_id, "tool_name": request.name, "safety_level": safety}

    result = await state.mcp.execute(request.name, request.arguments)
    return {"status": "error" if result.isError else "success", "content": result.content}

@app.get("/api/agent/pending")
def get_pending():
    return {"pending": list(state.pending_calls.values())}

@app.post("/api/agent/approve/{call_id}")
async def approve_call(call_id: str):
    if call_id not in state.pending_calls: raise HTTPException(status_code=404, detail="Not found")
    pending = state.pending_calls.pop(call_id)
    return await call_tool(ToolCallRequest(name=pending.name, arguments=pending.arguments, approved=True))

@app.post("/api/agent/reject/{call_id}")
def reject_call(call_id: str):
    if call_id not in state.pending_calls: raise HTTPException(status_code=404, detail="Not found")
    state.pending_calls.pop(call_id)
    return {"status": "rejected"}

# ========== CLI Entry ==========

def main():
    parser = argparse.ArgumentParser(description="BeyondCloud Local Agent")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sandbox", "-s", type=str)
    args = parser.parse_args()

    if args.sandbox:
        try:
            state.mcp = BeyondCloudLocalMCP(args.sandbox)
            state.sandbox_path = str(state.mcp.sandbox_path)
        except Exception as e: print(f"Error: {e}"); sys.exit(1)

    print(f"Starting BeyondCloud Proxy on port {args.port}...")
    uvicorn.run(app, host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
