"""
BeyondCloud Tools - Built-in MCP Server

Provides core tools:
- web_search: DuckDuckGo search
- screenshot: Webpage capture
- python_executor: Sandboxed Python
- database_query: Read-only SQL
"""
from .server import BeyondCloudToolsServer

__all__ = ["BeyondCloudToolsServer"]
