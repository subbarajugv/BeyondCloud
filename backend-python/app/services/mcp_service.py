"""
MCP Service - Model Context Protocol integration

Connects to external MCP servers for extended tool capabilities.
Tools discovered from MCP servers are merged with built-in tools
and made available to the agent.

Supports:
- stdio transport (local processes)
- HTTP/SSE transport (remote servers)
"""
import asyncio
import uuid
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from app.tracing import create_span, tracer


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection"""
    id: str
    name: str
    transport: str  # "stdio" or "http"
    command: Optional[str] = None  # For stdio: e.g., "npx"
    args: List[str] = field(default_factory=list)  # For stdio: e.g., ["server-filesystem", "/path"]
    url: Optional[str] = None  # For http transport
    env: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class MCPTool:
    """Tool definition from MCP server"""
    server_id: str
    server_name: str
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPService:
    """
    Model Context Protocol client service.
    
    Manages connections to MCP servers and provides:
    - Server management (add/remove/list)
    - Tool discovery (list tools from all servers)
    - Tool execution (call tools on specific servers)
    - OpenAI format conversion (for LLM function calling)
    - RBAC: Permission checks for user access
    """
    
    # RBAC: Role-based MCP access
    ROLE_MCP_PERMISSIONS = {
        "user": [],  # No MCP access
        "rag_user": [],  # No MCP access
        "agent_user": ["beyondcloud-tools"],  # Built-in only
        "agent_developer": ["beyondcloud-tools", "*custom*"],  # Built-in + custom
        "admin": ["*"],  # All servers
        "owner": ["*"],  # All servers
    }
    
    # Built-in MCP server config
    BUILTIN_SERVER = {
        "id": "beyondcloud-tools",
        "name": "beyondcloud-tools",
        "transport": "builtin",
        "is_builtin": True,
    }
    
    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._connections: Dict[str, Any] = {}  # Server ID -> active session
        self._tools_cache: Dict[str, List[MCPTool]] = {}  # Server ID -> tools
        self._builtin_server = None
    
    async def register_builtin_server(self):
        """Register the built-in BeyondCloud tools MCP server"""
        from mcp_servers.beyondcloud_tools import BeyondCloudToolsServer
        
        self._builtin_server = BeyondCloudToolsServer()
        
        # Register it in our servers list
        config = MCPServerConfig(
            id="beyondcloud-tools",
            name="BeyondCloud Tools",
            transport="builtin",
            is_active=True
        )
        self._servers["beyondcloud-tools"] = config
        
        # Get tools from built-in server
        tools_response = await self._builtin_server._handle_tools_list()
        self._tools_cache["beyondcloud-tools"] = [
            MCPTool(
                server_id="beyondcloud-tools",
                server_name="BeyondCloud Tools",
                name=t["name"],
                description=t["description"],
                input_schema=t["inputSchema"]
            )
            for t in tools_response.get("tools", [])
        ]
        
        return True
    
    def check_mcp_permission(self, user_role: str, server_id: str) -> bool:
        """
        Check if a user role has permission to use an MCP server.
        
        Args:
            user_role: User's role (user, rag_user, agent_user, admin, etc.)
            server_id: MCP server ID to check
            
        Returns:
            True if allowed, False if blocked
        """
        allowed = self.ROLE_MCP_PERMISSIONS.get(user_role, [])
        
        if "*" in allowed:
            return True  # Admin/owner can access all
        
        if server_id in allowed:
            return True  # Explicitly allowed server
        
        if "*custom*" in allowed and server_id not in ["beyondcloud-tools"]:
            return True  # Can access custom servers
        
        return False
    
    def get_allowed_servers(self, user_role: str) -> List[str]:
        """Get list of server IDs a user role can access"""
        allowed_patterns = self.ROLE_MCP_PERMISSIONS.get(user_role, [])
        
        if "*" in allowed_patterns:
            return list(self._servers.keys())
        
        result = []
        for server_id in self._servers.keys():
            if server_id in allowed_patterns:
                result.append(server_id)
            elif "*custom*" in allowed_patterns and server_id != "beyondcloud-tools":
                result.append(server_id)
        
        return result
    
    async def add_server(self, config: MCPServerConfig) -> str:
        """
        Add a new MCP server configuration.
        
        Args:
            config: Server configuration
            
        Returns:
            Server ID
        """
        async with create_span("mcp.add_server") as span:
            span.set_attribute("server_name", config.name)
            span.set_attribute("transport", config.transport)
            
            server_id = config.id or str(uuid.uuid4())
            config.id = server_id
            self._servers[server_id] = config
            
            # Try to connect and discover tools
            try:
                await self._connect_server(server_id)
                await self._discover_tools(server_id)
                span.set_status("OK")
            except Exception as e:
                span.set_status("ERROR", str(e))
                # Server added but not connected
                config.is_active = False
            
            return server_id
    
    async def remove_server(self, server_id: str) -> bool:
        """Remove an MCP server"""
        async with create_span("mcp.remove_server") as span:
            span.set_attribute("server_id", server_id)
            
            if server_id not in self._servers:
                span.set_status("ERROR", "Server not found")
                return False
            
            # Close connection if active
            if server_id in self._connections:
                await self._disconnect_server(server_id)
            
            del self._servers[server_id]
            self._tools_cache.pop(server_id, None)
            
            span.set_status("OK")
            return True
    
    def list_servers(self) -> List[MCPServerConfig]:
        """List all configured MCP servers"""
        return list(self._servers.values())
    
    async def list_tools(self, server_id: Optional[str] = None) -> List[MCPTool]:
        """
        List tools from MCP servers.
        
        Args:
            server_id: If provided, only list tools from this server
            
        Returns:
            List of available tools
        """
        async with create_span("mcp.list_tools") as span:
            if server_id:
                span.set_attribute("server_id", server_id)
                tools = self._tools_cache.get(server_id, [])
            else:
                tools = []
                for sid in self._servers:
                    tools.extend(self._tools_cache.get(sid, []))
            
            span.set_attribute("tool_count", len(tools))
            span.set_status("OK")
            return tools
    
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool on an MCP server.
        
        Args:
            server_id: The MCP server to use
            tool_name: Name of the tool to call
            args: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        async with create_span("mcp.call_tool") as span:
            span.set_attribute("server_id", server_id)
            span.set_attribute("tool_name", tool_name)
            
            if server_id not in self._servers:
                span.set_status("ERROR", "Server not found")
                return {"error": f"MCP server not found: {server_id}"}
            
            config = self._servers[server_id]
            
            # Handle built-in server
            if config.transport == "builtin" and self._builtin_server:
                try:
                    result = await self._builtin_server._execute_tool(tool_name, args)
                    span.set_status("OK")
                    return {
                        "status": "success" if not result.isError else "error",
                        "content": result.content,
                        "tool": tool_name,
                    }
                except Exception as e:
                    span.set_status("ERROR", str(e))
                    return {"error": str(e)}
            
            # For external servers, use stdio transport
            # TODO: Implement real MCP SDK integration
            try:
                result = await self._execute_tool_stdio(config, tool_name, args)
                span.set_status("OK")
                return result
            except Exception as e:

                span.set_status("ERROR", str(e))
                return {"error": str(e)}
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Convert all MCP tools to OpenAI function calling format.
        
        Returns:
            List of tools in OpenAI format
        """
        openai_tools = []
        
        for server_id, tools in self._tools_cache.items():
            for tool in tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": f"mcp_{tool.server_id}_{tool.name}",
                        "description": f"[MCP:{tool.server_name}] {tool.description}",
                        "parameters": tool.input_schema
                    }
                }
                openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def call_tool_by_openai_name(self, openai_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool using its OpenAI function name.
        
        Args:
            openai_name: Name in format "mcp_{server_id}_{tool_name}"
            args: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Parse the OpenAI name to get server_id and tool_name
        if not openai_name.startswith("mcp_"):
            return {"error": f"Invalid MCP tool name: {openai_name}"}
        
        parts = openai_name[4:].split("_", 1)
        if len(parts) != 2:
            return {"error": f"Invalid MCP tool name format: {openai_name}"}
        
        server_id, tool_name = parts
        return await self.call_tool(server_id, tool_name, args)
    
    # ========== Private Methods ==========
    
    async def _connect_server(self, server_id: str):
        """Connect to an MCP server"""
        config = self._servers[server_id]
        
        if config.transport == "stdio":
            # For stdio transport, we'll spawn the process when needed
            # The MCP SDK handles this, but for now we just validate config
            if not config.command:
                raise ValueError("Command required for stdio transport")
        elif config.transport == "http":
            if not config.url:
                raise ValueError("URL required for http transport")
        else:
            raise ValueError(f"Unknown transport: {config.transport}")
        
        config.is_active = True
    
    async def _disconnect_server(self, server_id: str):
        """Disconnect from an MCP server"""
        if server_id in self._connections:
            # Close the connection
            del self._connections[server_id]
        
        if server_id in self._servers:
            self._servers[server_id].is_active = False
    
    async def _discover_tools(self, server_id: str):
        """Discover tools from an MCP server"""
        config = self._servers[server_id]
        
        # TODO: Use real MCP SDK to discover tools
        # For now, return common tools based on known server types
        tools = []
        
        if config.command and "filesystem" in " ".join(config.args).lower():
            # Filesystem server tools
            tools = [
                MCPTool(
                    server_id=server_id,
                    server_name=config.name,
                    name="read_file",
                    description="Read contents of a file",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"}
                        },
                        "required": ["path"]
                    }
                ),
                MCPTool(
                    server_id=server_id,
                    server_name=config.name,
                    name="write_file",
                    description="Write content to a file",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "content": {"type": "string", "description": "Content to write"}
                        },
                        "required": ["path", "content"]
                    }
                ),
                MCPTool(
                    server_id=server_id,
                    server_name=config.name,
                    name="list_directory",
                    description="List contents of a directory",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the directory"}
                        },
                        "required": ["path"]
                    }
                ),
            ]
        
        self._tools_cache[server_id] = tools
    
    async def _execute_tool_stdio(
        self,
        config: MCPServerConfig,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool via stdio transport"""
        # TODO: Use real MCP SDK for tool execution
        # For now, simulate the execution
        
        # Build the command
        cmd = [config.command] + config.args if config.command else []
        
        # This is a placeholder - real implementation uses MCP SDK
        return {
            "status": "simulated",
            "tool": tool_name,
            "args": args,
            "message": "MCP tool execution simulated. Install @modelcontextprotocol/server-* for real execution.",
            "command": " ".join(cmd)
        }


# Singleton instance
mcp_service = MCPService()
