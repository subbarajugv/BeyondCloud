"""
MCP Router - API endpoints for MCP server management

Handles:
- Server configuration (add/remove/list)
- Tool discovery and execution
- Integration with agent tool calling

RBAC: Requires agent_user role or higher
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.mcp_service import mcp_service, MCPServerConfig
from app.tracing import create_span
from app.middleware.rbac import require_min_role
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.auth import get_current_user_id
from app.services.usage_service import usage_service


# RBAC: All MCP endpoints require agent_user role or higher
router = APIRouter(
    prefix="/api/mcp", 
    tags=["mcp"],
    dependencies=[require_min_role("agent_user")]
)


# ========== Request/Response Models ==========

class AddServerRequest(BaseModel):
    name: str
    transport: str  # "stdio" or "http"
    command: Optional[str] = None
    args: List[str] = []
    url: Optional[str] = None
    env: Dict[str, str] = {}


class AddServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    is_active: bool
    message: str


class ServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    command: Optional[str]
    args: List[str]
    url: Optional[str]
    is_active: bool


class ToolResponse(BaseModel):
    server_id: str
    server_name: str
    name: str
    description: str
    input_schema: Dict[str, Any]


class CallToolRequest(BaseModel):
    server_id: str
    tool_name: str
    args: Dict[str, Any] = {}


class CallToolResponse(BaseModel):
    status: str
    tool_name: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ========== Endpoints ==========

@router.get("/servers", response_model=List[ServerResponse])
async def list_servers():
    """List all configured MCP servers"""
    servers = mcp_service.list_servers()
    return [
        ServerResponse(
            id=s.id,
            name=s.name,
            transport=s.transport,
            command=s.command,
            args=s.args,
            url=s.url,
            is_active=s.is_active,
        )
        for s in servers
    ]


@router.post("/servers", response_model=AddServerResponse)
async def add_server(request: AddServerRequest):
    """
    Add a new MCP server connection.
    
    For stdio transport:
    - command: The executable (e.g., "npx", "python")
    - args: Arguments (e.g., ["@modelcontextprotocol/server-filesystem", "/path"])
    
    For http transport:
    - url: The server URL
    """
    async with create_span("mcp.api.add_server") as span:
        span.set_attribute("server_name", request.name)
        span.set_attribute("transport", request.transport)
        
        config = MCPServerConfig(
            id="",  # Will be generated
            name=request.name,
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
        )
        
        try:
            server_id = await mcp_service.add_server(config)
            server = mcp_service._servers.get(server_id)
            
            span.set_status("OK")
            return AddServerResponse(
                id=server_id,
                name=request.name,
                transport=request.transport,
                is_active=server.is_active if server else False,
                message=f"Server '{request.name}' added successfully"
            )
        except Exception as e:
            span.set_status("ERROR", str(e))
            raise HTTPException(status_code=400, detail=str(e))


@router.delete("/servers/{server_id}")
async def remove_server(server_id: str):
    """Remove an MCP server"""
    async with create_span("mcp.api.remove_server") as span:
        span.set_attribute("server_id", server_id)
        
        success = await mcp_service.remove_server(server_id)
        if not success:
            span.set_status("ERROR", "Server not found")
            raise HTTPException(status_code=404, detail="Server not found")
        
        span.set_status("OK")
        return {"message": "Server removed successfully"}


@router.get("/tools", response_model=List[ToolResponse])
async def list_tools(server_id: Optional[str] = None):
    """
    List available tools from MCP servers.
    
    Args:
        server_id: Optional filter by server
    """
    async with create_span("mcp.api.list_tools") as span:
        if server_id:
            span.set_attribute("server_id", server_id)
        
        tools = await mcp_service.list_tools(server_id)
        
        span.set_attribute("tool_count", len(tools))
        span.set_status("OK")
        
        return [
            ToolResponse(
                server_id=t.server_id,
                server_name=t.server_name,
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in tools
        ]


@router.post("/tools/call", response_model=CallToolResponse)
async def call_tool(
    request: CallToolRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Execute a tool on an MCP server"""
    async with create_span("mcp.api.call_tool") as span:
        span.set_attribute("server_id", request.server_id)
        span.set_attribute("tool_name", request.tool_name)
        
        result = await mcp_service.call_tool(
            server_id=request.server_id,
            tool_name=request.tool_name,
            args=request.args,
        )
        
        if "error" in result:
            span.set_status("ERROR", result["error"])
            return CallToolResponse(
                status="error",
                tool_name=request.tool_name,
                error=result["error"],
            )
        
        # Tracking: Increment MCP tool call
        await usage_service.increment(db, user_id, "mcp_tool_calls")
        
        span.set_status("OK")
        return CallToolResponse(
            status="success",
            tool_name=request.tool_name,
            result=result,
        )


@router.get("/tools/openai-format")
async def get_openai_tools():
    """
    Get all MCP tools in OpenAI function calling format.
    
    This can be merged with built-in tools when calling the LLM.
    """
    tools = mcp_service.get_openai_tools()
    return {"tools": tools, "count": len(tools)}
