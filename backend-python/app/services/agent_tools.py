"""
Agent Tools - File and command operations for the AI agent

All operations are sandboxed to a user-defined directory.
"""
import os
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.sandbox_service import SandboxGuard, classify_command


class ToolResult(Enum):
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
    Sandboxed tools for AI agent file operations and commands.
    
    All operations are constrained to the sandbox directory.
    """
    
    def __init__(self, sandbox_path: str):
        """
        Initialize agent tools with a sandbox directory.
        
        Args:
            sandbox_path: Absolute path to the sandbox directory
        """
        self.guard = SandboxGuard(sandbox_path)
        self.sandbox_path = Path(sandbox_path).resolve()
    
    # ========== File Operations ==========
    
    async def read_file(self, path: str) -> ToolResponse:
        """
        Read file content from sandbox.
        
        Args:
            path: Relative path within sandbox
        """
        try:
            is_safe, message = self.guard.is_safe_for_read(path)
            if not is_safe:
                return ToolResponse(
                    status=ToolResult.ERROR,
                    tool_name="read_file",
                    args={"path": path},
                    error=message
                )
            
            resolved = self.guard.resolve_path(path)
            content = resolved.read_text(encoding="utf-8")
            
            return ToolResponse(
                status=ToolResult.SUCCESS,
                tool_name="read_file",
                args={"path": path},
                result={"content": content, "size": len(content)},
                requires_approval=True,  # Default: requires approval
                safety_level="safe"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="read_file",
                args={"path": path},
                error=str(e)
            )
    
    async def write_file(self, path: str, content: str) -> ToolResponse:
        """
        Write content to a file in sandbox.
        
        Args:
            path: Relative path within sandbox
            content: Content to write
        """
        try:
            is_safe, message = self.guard.is_safe_for_write(path)
            if not is_safe:
                return ToolResponse(
                    status=ToolResult.ERROR,
                    tool_name="write_file",
                    args={"path": path, "content": f"[{len(content)} chars]"},
                    error=message
                )
            
            resolved = self.guard.resolve_path(path)
            
            # Create parent directories if needed
            resolved.parent.mkdir(parents=True, exist_ok=True)
            
            resolved.write_text(content, encoding="utf-8")
            
            return ToolResponse(
                status=ToolResult.SUCCESS,
                tool_name="write_file",
                args={"path": path, "content": f"[{len(content)} chars]"},
                result={"written": True, "size": len(content)},
                requires_approval=True,  # Write always requires approval by default
                safety_level="moderate"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="write_file",
                args={"path": path, "content": f"[{len(content)} chars]"},
                error=str(e)
            )
    
    async def list_dir(self, path: str = ".") -> ToolResponse:
        """
        List directory contents in sandbox.
        
        Args:
            path: Relative path within sandbox (default: root)
        """
        try:
            is_safe, message = self.guard.is_safe_for_list(path)
            if not is_safe:
                return ToolResponse(
                    status=ToolResult.ERROR,
                    tool_name="list_dir",
                    args={"path": path},
                    error=message
                )
            
            resolved = self.guard.resolve_path(path)
            entries = []
            
            for entry in resolved.iterdir():
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else None,
                })
            
            # Sort: directories first, then files
            entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
            
            return ToolResponse(
                status=ToolResult.SUCCESS,
                tool_name="list_dir",
                args={"path": path},
                result={"entries": entries, "count": len(entries)},
                requires_approval=False,  # list_dir is safe
                safety_level="safe"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="list_dir",
                args={"path": path},
                error=str(e)
            )
    
    async def search_files(self, pattern: str, path: str = ".") -> ToolResponse:
        """
        Search for files matching a pattern in sandbox.
        
        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.ts")
            path: Starting directory (default: root)
        """
        try:
            is_safe, message = self.guard.is_safe_for_list(path)
            if not is_safe:
                return ToolResponse(
                    status=ToolResult.ERROR,
                    tool_name="search_files",
                    args={"pattern": pattern, "path": path},
                    error=message
                )
            
            resolved = self.guard.resolve_path(path)
            matches = []
            
            for match in resolved.rglob(pattern):
                # Ensure match is within sandbox
                try:
                    rel_path = match.relative_to(self.sandbox_path)
                    matches.append({
                        "path": str(rel_path),
                        "is_dir": match.is_dir(),
                        "size": match.stat().st_size if match.is_file() else None,
                    })
                except ValueError:
                    continue  # Skip if somehow escapes sandbox
            
            return ToolResponse(
                status=ToolResult.SUCCESS,
                tool_name="search_files",
                args={"pattern": pattern, "path": path},
                result={"matches": matches[:100], "count": len(matches)},  # Limit results
                requires_approval=False,  # search is safe
                safety_level="safe"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="search_files",
                args={"pattern": pattern, "path": path},
                error=str(e)
            )
    
    # ========== Command Execution ==========
    
    async def run_command(
        self, 
        cmd: str, 
        timeout: int = 30
    ) -> ToolResponse:
        """
        Run a shell command in the sandbox directory.
        
        Args:
            cmd: Command to execute
            timeout: Timeout in seconds (default: 30)
        """
        # Classify command safety
        safety_level, safety_reason = classify_command(cmd)
        
        try:
            # Execute command with sandbox as cwd
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.sandbox_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "HOME": str(self.sandbox_path)}  # Restrict HOME
            )
            
            return ToolResponse(
                status=ToolResult.SUCCESS,
                tool_name="run_command",
                args={"cmd": cmd},
                result={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                },
                requires_approval=True,  # Commands ALWAYS require approval
                safety_level=safety_level
            )
        except subprocess.TimeoutExpired:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="run_command",
                args={"cmd": cmd},
                error=f"Command timed out after {timeout}s",
                safety_level=safety_level
            )
        except Exception as e:
            return ToolResponse(
                status=ToolResult.ERROR,
                tool_name="run_command",
                args={"cmd": cmd},
                error=str(e),
                safety_level=safety_level
            )


# Tool schema for LLM function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the sandbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file"
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
            "description": "Write content to a file in the sandbox",
            "parameters": {
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in a path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list (default: '.')"
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
            "description": "Search for files matching a glob pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '*.py', '**/*.ts')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory (default: '.')"
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
            "description": "Run a shell command in the sandbox directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["cmd"]
            }
        }
    }
]
