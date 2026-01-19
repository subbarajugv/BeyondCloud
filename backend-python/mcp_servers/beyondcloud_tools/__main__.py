"""
BeyondCloud Tools MCP Server - Main Entry Point

Run as: python -m mcp_servers.beyondcloud_tools
"""
import asyncio
import sys
from .server import BeyondCloudToolsServer


async def main():
    """Run the MCP server"""
    server = BeyondCloudToolsServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
