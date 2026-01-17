"""
Sandbox Service - Security guard for agentic file operations

Ensures all file operations stay within user-defined sandbox boundaries.
"""
import os
from pathlib import Path
from typing import Optional, Tuple


class SandboxGuard:
    """
    Security guard that validates all paths are within the sandbox.
    
    Prevents path traversal attacks like:
    - "../../../etc/passwd"
    - Symlinks pointing outside sandbox
    - Absolute paths outside sandbox
    """
    
    def __init__(self, sandbox_path: str):
        """
        Initialize sandbox guard with the allowed directory.
        
        Args:
            sandbox_path: Absolute path to the sandbox directory
        """
        self.sandbox_path = Path(sandbox_path).resolve()
        
        if not self.sandbox_path.exists():
            raise ValueError(f"Sandbox path does not exist: {sandbox_path}")
        if not self.sandbox_path.is_dir():
            raise ValueError(f"Sandbox path is not a directory: {sandbox_path}")
    
    def validate_path(self, path: str) -> Tuple[bool, str, Optional[Path]]:
        """
        Validate that a path is within the sandbox.
        
        Args:
            path: Relative or absolute path to validate
            
        Returns:
            Tuple of (is_valid, message, resolved_path)
        """
        try:
            # Handle relative paths
            if not os.path.isabs(path):
                full_path = (self.sandbox_path / path).resolve()
            else:
                full_path = Path(path).resolve()
            
            # Check if path is within sandbox
            try:
                full_path.relative_to(self.sandbox_path)
                return True, "Path is within sandbox", full_path
            except ValueError:
                return False, f"Path escapes sandbox: {path}", None
                
        except Exception as e:
            return False, f"Invalid path: {e}", None
    
    def resolve_path(self, path: str) -> Path:
        """
        Resolve a path within the sandbox, raising if invalid.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Resolved absolute path
            
        Raises:
            PermissionError: If path escapes sandbox
        """
        is_valid, message, resolved = self.validate_path(path)
        if not is_valid:
            raise PermissionError(message)
        return resolved
    
    def is_safe_for_read(self, path: str) -> Tuple[bool, str]:
        """Check if path is safe to read"""
        is_valid, message, resolved = self.validate_path(path)
        if not is_valid:
            return False, message
        if not resolved.exists():
            return False, f"File does not exist: {path}"
        if not resolved.is_file():
            return False, f"Not a file: {path}"
        return True, "OK"
    
    def is_safe_for_write(self, path: str) -> Tuple[bool, str]:
        """Check if path is safe to write"""
        is_valid, message, resolved = self.validate_path(path)
        if not is_valid:
            return False, message
        # Parent directory must exist and be within sandbox
        parent = resolved.parent
        try:
            parent.relative_to(self.sandbox_path)
        except ValueError:
            return False, f"Parent directory escapes sandbox"
        return True, "OK"
    
    def is_safe_for_list(self, path: str) -> Tuple[bool, str]:
        """Check if path is safe to list"""
        is_valid, message, resolved = self.validate_path(path)
        if not is_valid:
            return False, message
        if not resolved.exists():
            return False, f"Directory does not exist: {path}"
        if not resolved.is_dir():
            return False, f"Not a directory: {path}"
        return True, "OK"


# Command safety classification
SAFE_COMMANDS = {
    # Read-only commands
    "ls", "cat", "head", "tail", "less", "more", "wc", "file",
    "find", "grep", "egrep", "fgrep", "awk", "sed",
    "tree", "du", "df", "stat",
    # Development tools (read)
    "git status", "git log", "git diff", "git branch",
    "python --version", "node --version", "npm --version",
}

DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "rmdir",
    "sudo", "su ",
    "> /dev", ">/dev",
    "chmod 777", "chmod -R",
    "curl", "wget", "nc ", "netcat",
    "eval", "exec", 
    "$(", "`",  # Command substitution
    "&&", "||", ";",  # Command chaining (potential escape)
]


def classify_command(cmd: str) -> Tuple[str, str]:
    """
    Classify a command's safety level.
    
    Returns:
        Tuple of (level, reason)
        level: "safe", "moderate", "dangerous"
    """
    cmd_lower = cmd.lower().strip()
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return "dangerous", f"Contains dangerous pattern: {pattern}"
    
    # Check if it's a known safe command
    cmd_base = cmd_lower.split()[0] if cmd_lower else ""
    if cmd_base in SAFE_COMMANDS:
        return "safe", "Known safe command"
    
    # Default to moderate
    return "moderate", "Unknown command - requires approval"
