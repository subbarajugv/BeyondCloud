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
