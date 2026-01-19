"""
Agent Guardrails - Security checks for agent tool execution

Blocks dangerous commands, restricts file access paths, and logs all attempts.
"""
import re
import os
from typing import Tuple, Optional
from app.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# Command Blocklist
# =============================================================================

BLOCKED_COMMAND_PATTERNS = [
    # Destructive file operations
    r"rm\s+-rf",
    r"rm\s+-r\s+/",
    r"rm\s+/",
    r"rmdir\s+/",
    
    # Privilege escalation
    r"\bsudo\b",
    r"\bsu\s+-",
    r"\bdoas\b",
    
    # System modification
    r"chmod\s+777",
    r"chmod\s+-R\s+777",
    r"chown\s+-R",
    r"mkfs\b",
    r"fdisk\b",
    r"parted\b",
    
    # Dangerous redirects
    r">\s*/dev/",
    r"dd\s+if=",
    
    # Remote code execution
    r"curl\s+.*\|\s*sh",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"curl\s+.*-o\s*/",
    
    # Process/system control
    r"kill\s+-9\s+1\b",
    r"killall",
    r"pkill\s+-9",
    r"shutdown",
    r"reboot",
    r"init\s+0",
    r"init\s+6",
    
    # Environment manipulation
    r"export\s+PATH=",
    r"export\s+LD_PRELOAD",
    r"unset\s+PATH",
    
    # Disk operations
    r">\s*/etc/",
    r"echo\s+.*>\s*/etc/",
    
    # Fork bombs and resource exhaustion
    r":\(\)\s*{\s*:\|:",
    r"fork\s*bomb",
]

BLOCKED_COMMANDS_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in BLOCKED_COMMAND_PATTERNS]


# =============================================================================
# Path Restrictions
# =============================================================================

BLOCKED_PATHS = [
    "/etc",
    "/root",
    "/var",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/lib",
    "/lib64",
    "/opt",
    "/srv",
    "/mnt",
    "/media",
    "~/.ssh",
    "~/.gnupg",
    "~/.config",
    "~/.local/share",
]

# Paths that are always blocked even with path traversal
ABSOLUTE_BLOCKED_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/hosts",
    "/root/.ssh",
    "/root/.bashrc",
]


# =============================================================================
# Guardrail Functions
# =============================================================================

def check_command(command: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a command is safe to execute.
    
    Returns:
        (is_safe, blocked_reason) - (True, None) if safe, (False, reason) if blocked
    """
    if not command or not command.strip():
        return True, None
    
    command_lower = command.lower().strip()
    
    # Check against blocked patterns
    for pattern in BLOCKED_COMMANDS_COMPILED:
        if pattern.search(command_lower):
            reason = f"Command matches blocked pattern: {pattern.pattern}"
            logger.warning(f"BLOCKED COMMAND: {command[:100]}... Reason: {reason}")
            return False, reason
    
    return True, None


def check_path(path: str, sandbox_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if a file path is safe to access.
    
    Args:
        path: The path to check
        sandbox_path: Optional sandbox root - if provided, path must be within it
        
    Returns:
        (is_safe, blocked_reason) - (True, None) if safe, (False, reason) if blocked
    """
    if not path:
        return True, None
    
    # Normalize path
    path = os.path.expanduser(path)
    
    # Resolve to absolute path for comparison
    try:
        abs_path = os.path.abspath(path)
    except Exception:
        return False, "Invalid path format"
    
    # Check for path traversal attempts
    if ".." in path:
        # Resolve and check if it escapes sandbox
        if sandbox_path:
            sandbox_abs = os.path.abspath(os.path.expanduser(sandbox_path))
            if not abs_path.startswith(sandbox_abs):
                reason = f"Path traversal attempt detected: {path}"
                logger.warning(f"BLOCKED PATH: {reason}")
                return False, reason
    
    # Check absolute blocked paths
    for blocked in ABSOLUTE_BLOCKED_PATHS:
        blocked_expanded = os.path.expanduser(blocked)
        if abs_path == blocked_expanded or abs_path.startswith(blocked_expanded + "/"):
            reason = f"Access to {blocked} is forbidden"
            logger.warning(f"BLOCKED PATH: {path} -> {reason}")
            return False, reason
    
    # Check blocked path prefixes
    for blocked in BLOCKED_PATHS:
        blocked_expanded = os.path.expanduser(blocked)
        if abs_path.startswith(blocked_expanded):
            reason = f"Access to {blocked} is restricted"
            logger.warning(f"BLOCKED PATH: {path} -> {reason}")
            return False, reason
    
    # If sandbox is specified, ensure path is within it
    if sandbox_path:
        sandbox_abs = os.path.abspath(os.path.expanduser(sandbox_path))
        if not abs_path.startswith(sandbox_abs):
            reason = f"Path must be within sandbox: {sandbox_path}"
            logger.warning(f"BLOCKED PATH: {path} outside sandbox {sandbox_path}")
            return False, reason
    
    return True, None


def check_file_size(size_bytes: int, max_bytes: int = 10 * 1024 * 1024) -> Tuple[bool, Optional[str]]:
    """
    Check if file size is within limits (default 10MB).
    
    Returns:
        (is_safe, blocked_reason)
    """
    if size_bytes > max_bytes:
        reason = f"File size {size_bytes} exceeds limit of {max_bytes} bytes"
        return False, reason
    return True, None


def validate_tool_call(
    tool_name: str,
    args: dict,
    sandbox_path: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a tool call against all guardrails.
    
    Returns:
        (is_safe, blocked_reason)
    """
    # Command execution checks
    if tool_name in ["execute_command", "run_command", "shell"]:
        command = args.get("command") or args.get("cmd") or ""
        return check_command(command)
    
    # File operation checks
    if tool_name in ["read_file", "write_file", "delete_file", "list_dir"]:
        path = args.get("path") or args.get("file_path") or args.get("directory") or ""
        return check_path(path, sandbox_path)
    
    # File content checks
    if tool_name == "write_file":
        content = args.get("content") or ""
        content_bytes = len(content.encode("utf-8"))
        size_ok, size_reason = check_file_size(content_bytes)
        if not size_ok:
            return False, size_reason
    
    return True, None


# =============================================================================
# Audit Logging
# =============================================================================

def log_tool_execution(
    user_id: str,
    tool_name: str,
    args: dict,
    blocked: bool,
    reason: Optional[str] = None
):
    """
    Log tool execution attempt for audit trail.
    """
    status = "BLOCKED" if blocked else "ALLOWED"
    log_data = {
        "user_id": user_id,
        "tool": tool_name,
        "args": str(args)[:200],  # Truncate for logging
        "status": status,
        "reason": reason,
    }
    
    if blocked:
        logger.warning(f"Tool execution {status}: {log_data}")
    else:
        logger.info(f"Tool execution {status}: {log_data}")
