"""
BeyondCloud Tools - Built-in MCP Server (FastMCP)

Provides core tools:
- list_dir, read_file, write_file, search_files
- think, plan_task
- run_command, python_executor
- web_search, screenshot, database_query
"""
from .fastmcp_server import mcp

__all__ = ["mcp"]
