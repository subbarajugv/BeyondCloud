"""
Agent Router - API endpoints for agentic operations

Handles sandbox configuration, tool execution, and approval flow.

RBAC: Requires agent_user role or higher
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum

from app.services.agent_tools import AgentTools, ToolResponse, ToolResult, TOOL_SCHEMAS
from app.tracing import create_span, tracer
from app.middleware.rbac import require_min_role


# RBAC: All Agent endpoints require agent_user role or higher
router = APIRouter(
    prefix="/api/agent", 
    tags=["agent"],
    dependencies=[require_min_role("agent_user")]
)


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
    approved: bool = False  # Must be True if approval required


class ToolCallPending(BaseModel):
    """Pending tool call awaiting approval"""
    id: str
    tool_name: str
    args: Dict[str, Any]
    safety_level: str


# ========== In-memory State (per-session) ==========
# In production, use Redis or database

class AgentSession:
    """Per-user agent session state"""
    sandbox_path: Optional[str] = None
    approval_mode: ApprovalMode = ApprovalMode.REQUIRE_APPROVAL
    pending_calls: Dict[str, ToolCallPending] = {}
    tools: Optional[AgentTools] = None


# Simple in-memory session store (user_id -> session)
sessions: Dict[str, AgentSession] = {}


def get_session(user_id: str) -> AgentSession:
    """Get or create session for user"""
    if user_id not in sessions:
        sessions[user_id] = AgentSession()
    return sessions[user_id]


# ========== Endpoints ==========

@router.post("/set-sandbox")
async def set_sandbox(request: SetSandboxRequest, user_id: str = "default"):
    """
    Set the sandbox directory for agent operations.
    
    Args:
        path: Absolute path to the sandbox directory
    """
    async with create_span("agent.set_sandbox", {"path": request.path}) as span:
        session = get_session(user_id)
        
        try:
            # Validate and create tools
            tools = AgentTools(request.path)
            session.sandbox_path = request.path
            session.tools = tools
            
            span.set_status("OK")
            return {
                "success": True,
                "sandbox_path": request.path,
                "message": f"Sandbox set to: {request.path}"
            }
        except ValueError as e:
            span.set_status("ERROR", str(e))
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/set-mode")
async def set_mode(request: SetModeRequest, user_id: str = "default"):
    """
    Set the approval mode for tool execution.
    
    Modes:
    - require_approval: All tools need user approval (default)
    - trust_mode: Safe tools auto-execute, risky ones still need approval
    """
    session = get_session(user_id)
    session.approval_mode = request.mode
    
    return {
        "success": True,
        "mode": request.mode.value,
        "message": f"Approval mode set to: {request.mode.value}"
    }


@router.get("/status")
async def get_status(user_id: str = "default"):
    """Get current agent configuration status"""
    session = get_session(user_id)
    
    return {
        "sandbox_path": session.sandbox_path,
        "sandbox_active": session.tools is not None,
        "approval_mode": session.approval_mode.value,
        "pending_approvals": len(session.pending_calls),
    }


@router.get("/tools")
async def get_tools(include_mcp: bool = True):
    """
    Get available tool schemas for LLM function calling.
    
    Args:
        include_mcp: If True, merge MCP tools with built-in tools
        
    Returns:
        Combined list of tool schemas in OpenAI format
    """
    # Start with built-in tools
    all_tools = list(TOOL_SCHEMAS)
    
    # Add MCP tools if requested
    if include_mcp:
        from app.services.mcp_service import mcp_service
        mcp_tools = mcp_service.get_openai_tools()
        all_tools.extend(mcp_tools)
    
    return {
        "tools": all_tools,
        "builtin_count": len(TOOL_SCHEMAS),
        "mcp_count": len(all_tools) - len(TOOL_SCHEMAS),
    }


@router.post("/execute")
async def execute_tool(request: ExecuteToolRequest, user_id: str = "default"):
    """
    Execute a tool with approval check.
    
    Flow:
    1. If sandbox not set → error
    2. If tool requires approval and not approved → return pending
    3. If approved or trust mode → execute
    """
    async with create_span("agent.execute", {
        "tool_name": request.tool_name,
        "approved": request.approved,
    }) as span:
        session = get_session(user_id)
        
        if session.tools is None:
            span.set_status("ERROR", "Sandbox not configured")
            raise HTTPException(
                status_code=400, 
                detail="Sandbox not configured. Call /api/agent/set-sandbox first."
            )
        
        tools = session.tools
        tool_name = request.tool_name
        args = request.args
        
        span.set_attribute("tool_args", str(args)[:200])  # Truncate for safety
        
        # Determine if approval is needed
        needs_approval = True
        
        if session.approval_mode == ApprovalMode.TRUST_MODE:
            # In trust mode, only commands always need approval
            if tool_name != "run_command":
                needs_approval = False
        
        # If not approved and needs approval, return pending
        if needs_approval and not request.approved:
            import uuid
            call_id = str(uuid.uuid4())
            
            # Get safety level for commands
            safety_level = "moderate"
            if tool_name == "run_command":
                from app.services.sandbox_service import classify_command
                safety_level, _ = classify_command(args.get("cmd", ""))
            
            pending = ToolCallPending(
                id=call_id,
                tool_name=tool_name,
                args=args,
                safety_level=safety_level
            )
            session.pending_calls[call_id] = pending
            
            span.set_attribute("status", "pending_approval")
            span.set_attribute("call_id", call_id)
            span.set_attribute("safety_level", safety_level)
            
            return {
                "status": "pending_approval",
                "call_id": call_id,
                "tool_name": tool_name,
                "args": args,
                "safety_level": safety_level,
                "message": "Tool call requires approval"
            }
        
        # Execute the tool
        span.add_event("executing_tool")
        result: ToolResponse
        
        if tool_name == "read_file":
            result = await tools.read_file(args.get("path", ""))
        elif tool_name == "write_file":
            result = await tools.write_file(args.get("path", ""), args.get("content", ""))
        elif tool_name == "list_dir":
            result = await tools.list_dir(args.get("path", "."))
        elif tool_name == "search_files":
            result = await tools.search_files(args.get("pattern", "*"), args.get("path", "."))
        elif tool_name == "run_command":
            result = await tools.run_command(args.get("cmd", ""))
        # Phase 8: Advanced Tools
        elif tool_name == "web_search":
            result = await tools.web_search(args.get("query", ""), args.get("num_results", 5))
        elif tool_name == "rag_query":
            result = await tools.rag_query(args.get("query", ""), args.get("top_k", 5))
        elif tool_name == "run_python":
            result = await tools.run_python(args.get("code", ""), args.get("timeout", 10))
        else:
            span.set_status("ERROR", f"Unknown tool: {tool_name}")
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        span.set_attribute("result_status", result.status.value)
        if result.error:
            span.set_status("ERROR", result.error)
        else:
            span.set_status("OK")
        
        return {
            "status": result.status.value,
            "tool_name": result.tool_name,
            "args": result.args,
            "result": result.result,
            "error": result.error,
        }


@router.post("/approve/{call_id}")
async def approve_call(call_id: str, user_id: str = "default"):
    """Approve a pending tool call"""
    session = get_session(user_id)
    
    if call_id not in session.pending_calls:
        raise HTTPException(status_code=404, detail="Pending call not found")
    
    pending = session.pending_calls.pop(call_id)
    
    # Execute with approved=True
    return await execute_tool(
        ExecuteToolRequest(
            tool_name=pending.tool_name,
            args=pending.args,
            approved=True
        ),
        user_id
    )


@router.post("/reject/{call_id}")
async def reject_call(call_id: str, user_id: str = "default"):
    """Reject a pending tool call"""
    session = get_session(user_id)
    
    if call_id not in session.pending_calls:
        raise HTTPException(status_code=404, detail="Pending call not found")
    
    pending = session.pending_calls.pop(call_id)
    
    return {
        "status": "rejected",
        "tool_name": pending.tool_name,
        "message": "Tool call rejected by user"
    }


@router.get("/pending")
async def get_pending_calls(user_id: str = "default"):
    """Get all pending tool calls awaiting approval"""
    session = get_session(user_id)
    
    return {
        "pending": [
            {
                "id": p.id,
                "tool_name": p.tool_name,
                "args": p.args,
                "safety_level": p.safety_level,
            }
            for p in session.pending_calls.values()
        ]
    }
