"""
BeyondCloud Tools - FastMCP Server

Migrated to FastMCP for cleaner code and better transport support.
Includes tracing/observability integration.
"""
import logging
from pathlib import Path
from typing import Optional
from functools import wraps

from fastmcp import FastMCP

# Tracing integration
from app.tracing import create_span

logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("BeyondCloud Tools")

# Default sandbox path (can be overridden)
SANDBOX_PATH = Path("/tmp/beyondcloud-sandbox")


def traced(span_name: str):
    """Decorator to add tracing to MCP tools"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with create_span(f"mcp.tool.{span_name}", kwargs):
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator


def _check_sandbox(path: str) -> tuple[Path, Optional[str]]:
    """Validate path is within sandbox. Returns (full_path, error_or_none)"""
    try:
        full_path = (SANDBOX_PATH / path).resolve()
        if not str(full_path).startswith(str(SANDBOX_PATH.resolve())):
            return full_path, "Path outside sandbox"
        return full_path, None
    except Exception as e:
        return SANDBOX_PATH, f"Invalid path: {e}"


# =============================================================================
# Core Tools (No External Dependencies)
# =============================================================================

@mcp.tool
def list_dir(path: str = ".") -> str:
    """List files and directories in the sandbox"""
    full_path, error = _check_sandbox(path)
    if error:
        return f"Error: {error}"
    
    if not full_path.exists():
        return f"Directory not found: {path}"
    
    entries = []
    for entry in full_path.iterdir():
        prefix = "📁 " if entry.is_dir() else "📄 "
        entries.append(f"{prefix}{entry.name}")
    
    entries.sort()
    return "\n".join(entries) or "(empty)"


@mcp.tool
def read_file(path: str) -> str:
    """Read the contents of a file in the sandbox"""
    full_path, error = _check_sandbox(path)
    if error:
        return f"Error: {error}"
    
    if not full_path.exists():
        return f"File not found: {path}"
    
    try:
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Read error: {e}"


@mcp.tool
def write_file(path: str, content: str) -> str:
    """Write content to a file in the sandbox"""
    full_path, error = _check_sandbox(path)
    if error:
        return f"Error: {error}"
    
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"Write error: {e}"


@mcp.tool
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob pattern"""
    full_path, error = _check_sandbox(path)
    if error:
        return f"Error: {error}"
    
    matches = list(full_path.rglob(pattern))[:50]
    results = [str(m.relative_to(SANDBOX_PATH)) for m in matches]
    return "\n".join(results) or "(no matches)"


@mcp.tool
def think(thought: str) -> str:
    """Record a reasoning step without executing any action"""
    return f"💭 Thought recorded ({len(thought)} chars)"


@mcp.tool
def plan_task(goal: str, steps: list[str]) -> str:
    """Create an execution plan for a complex task"""
    plan = f"📋 **Plan: {goal}**\n\n"
    for i, step in enumerate(steps, 1):
        plan += f"{i}. {step}\n"
    return plan


# =============================================================================
# Guarded Tools (With Security Checks)
# =============================================================================

@mcp.tool
def run_command(cmd: str, timeout: int = 30) -> str:
    """Run a shell command in the sandbox directory (with safety checks)"""
    import subprocess
    
    # Security: Use guardrails
    try:
        from app.services.agent_guardrails import check_command
        is_safe, reason = check_command(cmd)
        if not is_safe:
            return f"Blocked: {reason}"
    except ImportError:
        logger.warning("Guardrails not available, running command anyway")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(SANDBOX_PATH),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        output += f"\n[exit code]: {result.returncode}"
        return output or "(no output)"
        
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def python_executor(code: str, timeout: int = 10) -> str:
    """Execute Python code in a sandboxed environment"""
    import subprocess
    import tempfile
    import os
    
    # Security: Block dangerous imports
    BLOCKED = ["os", "sys", "subprocess", "shutil", "socket"]
    for blocked in BLOCKED:
        if f"import {blocked}" in code or f"from {blocked}" in code:
            return f"Import of {blocked} is not allowed"
    
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
        return output or "(no output)"
        
    except subprocess.TimeoutExpired:
        return f"Execution timed out after {timeout}s"
    finally:
        os.unlink(script_path)


# =============================================================================
# External Tools
# =============================================================================

@mcp.tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo"""
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        
        formatted = [
            f"**{r.get('title', '')}**\n{r.get('href', '')}\n{r.get('body', '')}"
            for r in results
        ]
        return "\n\n".join(formatted) or "(no results)"
    except ImportError:
        return "DuckDuckGo search not available (pip install duckduckgo-search)"
    except Exception as e:
        return f"Search error: {e}"


@mcp.tool
async def screenshot(url: str, full_page: bool = False) -> str:
    """Capture a screenshot of a webpage"""
    try:
        from playwright.async_api import async_playwright
        import base64
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            screenshot_bytes = await page.screenshot(full_page=full_page)
            await browser.close()
        
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return f"Screenshot captured ({len(screenshot_bytes)} bytes). Base64: {screenshot_b64[:100]}..."
    except ImportError:
        return "Playwright not available (pip install playwright && playwright install)"
    except Exception as e:
        return f"Screenshot error: {e}"


@mcp.tool
async def database_query(sql: str) -> str:
    """Execute a read-only SQL SELECT query"""
    # Security: Only allow SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith(("SELECT", "WITH")):
        return "Only SELECT queries are allowed"
    
    BLOCKED = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
    for blocked in BLOCKED:
        if blocked in sql_upper:
            return f"{blocked} statements are not allowed"
    
    try:
        from app.database import get_db_context
        from sqlalchemy import text
        
        async with get_db_context() as db:
            result = await db.execute(text(sql))
            rows = result.mappings().all()
            data = [dict(row) for row in rows[:100]]
        
        if not data:
            return "(no results)"
        
        # Format as table
        headers = list(data[0].keys())
        output = " | ".join(headers) + "\n"
        output += "-" * len(output) + "\n"
        for row in data:
            output += " | ".join(str(row.get(h, "")) for h in headers) + "\n"
        return output
        
    except ImportError:
        return "Database not available in this context"
    except Exception as e:
        return f"Database error: {e}"


# =============================================================================
# Server Entry Point
# =============================================================================

def set_sandbox(path: str):
    """Update the sandbox path"""
    global SANDBOX_PATH
    SANDBOX_PATH = Path(path).resolve()
    SANDBOX_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"Sandbox set to: {SANDBOX_PATH}")


if __name__ == "__main__":
    import asyncio
    mcp.run()
