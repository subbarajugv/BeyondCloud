"""
Agent Tools - Core classes for agent tool execution

NOTE: Tool implementations have been moved to MCP server:
      mcp_servers/beyondcloud_tools/server.py

This file now only contains core classes used by the agent router.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.services.sandbox_service import SandboxGuard


class ToolResult(Enum):
    """Tool execution status"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"


@dataclass
class ToolResponse:
    """Response from a tool execution"""
    status: ToolResult
    tool_name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    requires_approval: bool = False
    safety_level: str = "moderate"


class AgentTools:
    """
    Agent tools manager - validates sandbox and delegates to MCP server.
    
    All tool implementations are now in the BeyondCloud MCP server.
    This class handles sandbox validation and approval flow.
    """
    
    def __init__(self, sandbox_path: str):
        """
        Initialize agent tools with a sandbox directory.
        
        Args:
            sandbox_path: Absolute path to the sandbox directory
        """
        self.guard = SandboxGuard(sandbox_path)
        self.sandbox_path = Path(sandbox_path).resolve()
    
    def get_sandbox_path(self) -> str:
        """Get the configured sandbox path"""
        return str(self.sandbox_path)
    
    def validate_sandbox(self) -> bool:
        """Check if sandbox is properly configured"""
        return self.sandbox_path.exists() and self.sandbox_path.is_dir()


# Tool schemas for LLM function calling
# These are now served from MCP server via /api/mcp/tools
TOOL_SCHEMAS = []  # Deprecated - use mcp_service.get_openai_tools() instead
