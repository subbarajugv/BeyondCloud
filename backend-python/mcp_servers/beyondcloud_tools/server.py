"""
BeyondCloud Tools MCP Server

Async MCP server implementation providing built-in tools:
- web_search
- screenshot  
- python_executor
- database_query
"""
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


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


class BeyondCloudToolsServer:
    """
    MCP Server for BeyondCloud built-in tools.
    
    Implements the Model Context Protocol for tool discovery and execution.
    """
    
    def __init__(self, sandbox_path: Optional[str] = None):
        self.sandbox_path = sandbox_path or "/tmp/beyondcloud-sandbox"
        self._tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Tool]:
        """Register all available tools"""
        return {
            "web_search": Tool(
                name="web_search",
                description="Search the web using DuckDuckGo",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            "screenshot": Tool(
                name="screenshot",
                description="Capture a screenshot of a webpage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to screenshot"
                        },
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page (default: false)",
                            "default": False
                        }
                    },
                    "required": ["url"]
                }
            ),
            "python_executor": Tool(
                name="python_executor",
                description="Execute Python code in a sandboxed environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["code"]
                }
            ),
            "database_query": Tool(
                name="database_query",
                description="Execute a read-only SQL SELECT query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query"
                        }
                    },
                    "required": ["sql"]
                }
            ),
            # ===== File Tools =====
            "read_file": Tool(
                name="read_file",
                description="Read the contents of a file in the sandbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file"
                        }
                    },
                    "required": ["path"]
                }
            ),
            "write_file": Tool(
                name="write_file",
                description="Write content to a file in the sandbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        }
                    },
                    "required": ["path", "content"]
                }
            ),
            "list_dir": Tool(
                name="list_dir",
                description="List files and directories in a path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to list (default: '.')",
                            "default": "."
                        }
                    },
                    "required": []
                }
            ),
            "search_files": Tool(
                name="search_files",
                description="Search for files matching a glob pattern",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '*.py', '**/*.ts')"
                        },
                        "path": {
                            "type": "string",
                            "description": "Starting directory (default: '.')",
                            "default": "."
                        }
                    },
                    "required": ["pattern"]
                }
            ),
            # ===== Exec Tools =====
            "run_command": Tool(
                name="run_command",
                description="Run a shell command in the sandbox directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cmd": {
                            "type": "string",
                            "description": "Shell command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30
                        }
                    },
                    "required": ["cmd"]
                }
            ),
            # ===== Planning Tools =====
            "think": Tool(
                name="think",
                description="Record a thought or reasoning step without executing any action. Use this to think through problems before acting.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thought": {
                            "type": "string",
                            "description": "The reasoning or thought to record"
                        }
                    },
                    "required": ["thought"]
                }
            ),
            "plan_task": Tool(
                name="plan_task",
                description="Create an execution plan for a complex task. Use this before performing multi-step operations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "description": "The goal to accomplish"
                        },
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of steps to execute"
                        }
                    },
                    "required": ["goal", "steps"]
                }
            ),
        }

    
    # =========================================================================
    # MCP Protocol Handlers
    # =========================================================================
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
            
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        
        except Exception as e:
            logger.exception(f"Error handling request: {e}")
            return self._error_response(request_id, -32603, str(e))
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "beyondcloud-tools",
                "version": "1.0.0"
            }
        }
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [asdict(tool) for tool in self._tools.values()]
        return {"tools": tools}
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Execute the tool
        result = await self._execute_tool(tool_name, arguments)
        return asdict(result)
    
    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }
    
    # =========================================================================
    # Tool Implementations
    # =========================================================================
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return result"""
        try:
            if tool_name == "web_search":
                return await self._web_search(args)
            elif tool_name == "screenshot":
                return await self._screenshot(args)
            elif tool_name == "python_executor":
                return await self._python_executor(args)
            elif tool_name == "database_query":
                return await self._database_query(args)
            # File tools
            elif tool_name == "read_file":
                return await self._read_file(args)
            elif tool_name == "write_file":
                return await self._write_file(args)
            elif tool_name == "list_dir":
                return await self._list_dir(args)
            elif tool_name == "search_files":
                return await self._search_files(args)
            # Exec tools
            elif tool_name == "run_command":
                return await self._run_command(args)
            # Planning tools
            elif tool_name == "think":
                return await self._think(args)
            elif tool_name == "plan_task":
                return await self._plan_task(args)
            else:
                return ToolResult(
                    content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    isError=True
                )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                isError=True
            )
    
    async def _web_search(self, args: Dict[str, Any]) -> ToolResult:
        """Execute web search"""
        from duckduckgo_search import DDGS
        
        query = args.get("query", "")
        num_results = args.get("num_results", 5)
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        
        formatted = [
            f"**{r.get('title', '')}**\n{r.get('href', '')}\n{r.get('body', '')}"
            for r in results
        ]
        
        return ToolResult(
            content=[{"type": "text", "text": "\n\n".join(formatted)}]
        )
    
    async def _screenshot(self, args: Dict[str, Any]) -> ToolResult:
        """Capture webpage screenshot"""
        from playwright.async_api import async_playwright
        import base64
        
        url = args.get("url", "")
        full_page = args.get("full_page", False)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            screenshot_bytes = await page.screenshot(full_page=full_page)
            await browser.close()
        
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        return ToolResult(
            content=[{
                "type": "image",
                "data": screenshot_b64,
                "mimeType": "image/png"
            }]
        )
    
    async def _python_executor(self, args: Dict[str, Any]) -> ToolResult:
        """Execute Python code in sandbox"""
        import subprocess
        import tempfile
        import os
        
        code = args.get("code", "")
        timeout = args.get("timeout", 10)
        
        # Security: Block dangerous imports
        BLOCKED_IMPORTS = ["os", "sys", "subprocess", "shutil", "socket"]
        for blocked in BLOCKED_IMPORTS:
            if f"import {blocked}" in code or f"from {blocked}" in code:
                return ToolResult(
                    content=[{"type": "text", "text": f"Import of {blocked} is not allowed"}],
                    isError=True
                )
        
        # Create temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            script_path = f.name
        
        try:
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={'PATH': os.environ.get('PATH', '')}
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            
            return ToolResult(
                content=[{"type": "text", "text": output or "(no output)"}]
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                content=[{"type": "text", "text": f"Execution timed out after {timeout}s"}],
                isError=True
            )
        finally:
            os.unlink(script_path)
    
    async def _database_query(self, args: Dict[str, Any]) -> ToolResult:
        """Execute read-only SQL query"""
        sql = args.get("sql", "")
        
        # Security: Only allow SELECT
        ALLOWED_KEYWORDS = ["SELECT", "WITH"]
        BLOCKED_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", 
                           "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXEC"]
        
        sql_upper = sql.strip().upper()
        
        if not any(sql_upper.startswith(kw) for kw in ALLOWED_KEYWORDS):
            return ToolResult(
                content=[{"type": "text", "text": "Only SELECT queries are allowed"}],
                isError=True
            )
        
        for blocked in BLOCKED_KEYWORDS:
            if blocked in sql_upper:
                return ToolResult(
                    content=[{"type": "text", "text": f"{blocked} statements are not allowed"}],
                    isError=True
                )
        
        try:
            # Import here to avoid circular dependency
            from app.database import get_db_context
            from sqlalchemy import text
            
            async with get_db_context() as db:
                result = await db.execute(text(sql))
                rows = result.mappings().all()
                data = [dict(row) for row in rows[:100]]
            
            # Format as table
            if data:
                headers = list(data[0].keys())
                output = " | ".join(headers) + "\n"
                output += "-" * len(output) + "\n"
                for row in data:
                    output += " | ".join(str(row.get(h, "")) for h in headers) + "\n"
            else:
                output = "(no results)"
            
            return ToolResult(
                content=[{"type": "text", "text": output}]
            )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Database error: {str(e)}"}],
                isError=True
            )
    
    # ===== File Tool Implementations =====
    
    async def _read_file(self, args: Dict[str, Any]) -> ToolResult:
        """Read file contents"""
        from pathlib import Path
        
        path = args.get("path", "")
        sandbox = Path(self.sandbox_path)
        full_path = sandbox / path
        
        # Security: ensure within sandbox
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(sandbox.resolve())):
                return ToolResult(
                    content=[{"type": "text", "text": "Path outside sandbox"}],
                    isError=True
                )
        except Exception:
            return ToolResult(
                content=[{"type": "text", "text": "Invalid path"}],
                isError=True
            )
        
        if not full_path.exists():
            return ToolResult(
                content=[{"type": "text", "text": f"File not found: {path}"}],
                isError=True
            )
        
        try:
            content = full_path.read_text(encoding="utf-8")
            return ToolResult(
                content=[{"type": "text", "text": content}]
            )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Read error: {str(e)}"}],
                isError=True
            )
    
    async def _write_file(self, args: Dict[str, Any]) -> ToolResult:
        """Write file contents"""
        from pathlib import Path
        
        path = args.get("path", "")
        content = args.get("content", "")
        sandbox = Path(self.sandbox_path)
        full_path = sandbox / path
        
        # Security: ensure within sandbox
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(sandbox.resolve())):
                return ToolResult(
                    content=[{"type": "text", "text": "Path outside sandbox"}],
                    isError=True
                )
        except Exception:
            return ToolResult(
                content=[{"type": "text", "text": "Invalid path"}],
                isError=True
            )
        
        try:
            full_path.write_text(content, encoding="utf-8")
            return ToolResult(
                content=[{"type": "text", "text": f"Written {len(content)} chars to {path}"}]
            )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Write error: {str(e)}"}],
                isError=True
            )
    
    async def _list_dir(self, args: Dict[str, Any]) -> ToolResult:
        """List directory contents"""
        from pathlib import Path
        
        path = args.get("path", ".")
        sandbox = Path(self.sandbox_path)
        full_path = (sandbox / path).resolve()
        
        if not str(full_path).startswith(str(sandbox.resolve())):
            return ToolResult(
                content=[{"type": "text", "text": "Path outside sandbox"}],
                isError=True
            )
        
        if not full_path.exists():
            return ToolResult(
                content=[{"type": "text", "text": f"Directory not found: {path}"}],
                isError=True
            )
        
        entries = []
        for entry in full_path.iterdir():
            prefix = "📁 " if entry.is_dir() else "📄 "
            entries.append(f"{prefix}{entry.name}")
        
        entries.sort()
        return ToolResult(
            content=[{"type": "text", "text": "\n".join(entries) or "(empty)"}]
        )
    
    async def _search_files(self, args: Dict[str, Any]) -> ToolResult:
        """Search for files by pattern"""
        from pathlib import Path
        
        pattern = args.get("pattern", "*")
        path = args.get("path", ".")
        sandbox = Path(self.sandbox_path)
        full_path = (sandbox / path).resolve()
        
        if not str(full_path).startswith(str(sandbox.resolve())):
            return ToolResult(
                content=[{"type": "text", "text": "Path outside sandbox"}],
                isError=True
            )
        
        matches = list(full_path.rglob(pattern))[:50]  # Limit results
        results = [str(m.relative_to(sandbox)) for m in matches]
        
        return ToolResult(
            content=[{"type": "text", "text": "\n".join(results) or "(no matches)"}]
        )
    
    # ===== Exec Tool Implementations =====
    
    async def _run_command(self, args: Dict[str, Any]) -> ToolResult:
        """Run shell command in sandbox"""
        import subprocess
        import os
        
        cmd = args.get("cmd", "")
        timeout = args.get("timeout", 30)
        
        # Security checks via guardrails
        from app.services.agent_guardrails import check_command
        is_safe, reason = check_command(cmd)
        if not is_safe:
            return ToolResult(
                content=[{"type": "text", "text": f"Blocked: {reason}"}],
                isError=True
            )
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.sandbox_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            output += f"\n[exit code]: {result.returncode}"
            
            return ToolResult(
                content=[{"type": "text", "text": output or "(no output)"}]
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                content=[{"type": "text", "text": f"Timeout after {timeout}s"}],
                isError=True
            )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                isError=True
            )
    
    # ===== Planning Tool Implementations =====
    
    async def _think(self, args: Dict[str, Any]) -> ToolResult:
        """Record a thought without action"""
        thought = args.get("thought", "")
        
        # Just acknowledge the thought - helps agent reason without filling context
        return ToolResult(
            content=[{"type": "text", "text": f"💭 Thought recorded ({len(thought)} chars)"}]
        )
    
    async def _plan_task(self, args: Dict[str, Any]) -> ToolResult:
        """Create execution plan"""
        goal = args.get("goal", "")
        steps = args.get("steps", [])
        
        plan_text = f"📋 **Plan: {goal}**\n\n"
        for i, step in enumerate(steps, 1):
            plan_text += f"{i}. {step}\n"
        
        return ToolResult(
            content=[{"type": "text", "text": plan_text}]
        )
    
    # =========================================================================
    # STDIO Transport
    # =========================================================================
    
    async def run_stdio(self):
        """Run MCP server over stdio"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                
                request = json.loads(line.decode())
                response = await self.handle_request(request)
                
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
            except Exception as e:
                logger.exception(f"Error in stdio loop: {e}")
                break

