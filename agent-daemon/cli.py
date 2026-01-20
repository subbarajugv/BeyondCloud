#!/usr/bin/env python3
"""
BeyondCloud Agent CLI

Run the agent from command line with local or remote LLM & tools.

Usage:
    # Local mode (default) - uses FastMCP directly
    beyondcloud "Create a hello world script"
    
    # Remote mode - connects to backend with auth
    beyondcloud "Deploy the app" --remote --token $BEYONDCLOUD_TOKEN
"""

import asyncio
import argparse
import sys
import os
import logging
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("beyondcloud")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BeyondCloud Agent - AI-powered assistant with tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Local mode with Ollama (default)
    beyondcloud "List files in current directory"

    # Remote mode with backend authentication
    beyondcloud "Deploy the app" --remote --token $BEYONDCLOUD_TOKEN
    
    # Custom LLM endpoint
    beyondcloud "Explain this code" --llm http://localhost:8080/v1
        """
    )
    
    parser.add_argument(
        "goal",
        nargs="?",
        help="The task/goal for the agent to accomplish"
    )
    
    parser.add_argument(
        "--llm", "-l",
        default=os.environ.get("BEYONDCLOUD_LLM_URL", "http://localhost:11434/v1"),
        help="LLM API endpoint (default: Ollama on localhost:11434)"
    )
    
    parser.add_argument(
        "--model", "-m",
        default=os.environ.get("BEYONDCLOUD_MODEL", "qwen2.5:3b"),
        help="Model name (default: qwen2.5:3b)"
    )
    
    parser.add_argument(
        "--remote", "-r",
        action="store_true",
        help="Use remote backend API instead of local FastMCP"
    )
    
    parser.add_argument(
        "--backend",
        default=os.environ.get("BEYONDCLOUD_BACKEND", "http://localhost:8001"),
        help="Backend URL for remote mode (default: localhost:8001)"
    )
    
    parser.add_argument(
        "--token", "-t",
        default=os.environ.get("BEYONDCLOUD_TOKEN"),
        help="Auth token for remote mode (reads from $BEYONDCLOUD_TOKEN)"
    )
    
    parser.add_argument(
        "--sandbox",
        default=os.environ.get("BEYONDCLOUD_SANDBOX", "/tmp/beyondcloud-sandbox"),
        help="Sandbox directory for file operations"
    )
    
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum agent loop iterations (default: 10)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode - prompt for goals"
    )
    
    return parser.parse_args()


class LocalToolExecutor:
    """Execute tools directly via FastMCP (local mode)."""
    
    def __init__(self, sandbox_path: str):
        self.sandbox_path = sandbox_path
        self._mcp = None
    
    async def init(self):
        """Initialize FastMCP server."""
        # Import here to avoid circular imports and allow remote-only use
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend-python"))
        from mcp_servers.beyondcloud_tools.fastmcp_server import mcp, set_sandbox
        
        self._mcp = mcp
        set_sandbox(self.sandbox_path)
        logger.info(f"Local tools initialized (sandbox: {self.sandbox_path})")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools in OpenAI format."""
        if not self._mcp:
            return []
        
        tools = []
        for name, tool in self._mcp._tool_manager._tools.items():
            tools.append({
                "name": name,
                "description": tool.description or "",
                "inputSchema": tool.parameters if isinstance(tool.parameters, dict) else {},
            })
        return tools
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return result."""
        if not self._mcp:
            return "Error: Tools not initialized"
        
        tool = self._mcp._tool_manager._tools.get(name)
        if not tool:
            return f"Error: Tool not found: {name}"
        
        try:
            if asyncio.iscoroutinefunction(tool.fn):
                result = await tool.fn(**args)
            else:
                result = tool.fn(**args)
            return str(result)
        except Exception as e:
            return f"Error: {e}"


class RemoteToolExecutor:
    """Execute tools via HTTP API (remote mode)."""
    
    def __init__(self, backend_url: str, token: str):
        self.backend_url = backend_url.rstrip("/")
        self.token = token
        self._http = None
        self._tools = []
    
    async def init(self):
        """Initialize HTTP client and discover tools."""
        import httpx
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        self._http = httpx.AsyncClient(timeout=120, headers=headers)
        
        # Discover tools
        try:
            resp = await self._http.get(f"{self.backend_url}/api/mcp/tools")
            if resp.status_code == 200:
                data = resp.json()
                self._tools = data.get("tools", [])
                logger.info(f"Remote tools discovered: {len(self._tools)}")
            else:
                logger.warning(f"Failed to discover tools: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to discover tools: {e}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools."""
        return self._tools
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a tool via HTTP API."""
        if not self._http:
            return "Error: Not connected"
        
        try:
            resp = await self._http.post(
                f"{self.backend_url}/api/mcp/tools/call",
                json={
                    "server_id": "beyondcloud-tools",
                    "tool_name": name,
                    "args": args
                }
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "success":
                    content = result.get("result", {}).get("content", [])
                    if content:
                        return content[0].get("text", str(result))
                    return str(result)
                return result.get("error", "Unknown error")
            elif resp.status_code == 401:
                return "Error: Unauthorized - please provide --token"
            else:
                return f"Error: HTTP {resp.status_code}"
        except Exception as e:
            return f"Error: {e}"
    
    async def close(self):
        """Close HTTP client."""
        if self._http:
            await self._http.aclose()


async def run_agent(goal: str, args) -> str:
    """Run the agent with the given goal."""
    from agent import Agent, AgentConfig
    
    # Initialize tool executor
    if args.remote:
        if not args.token:
            logger.warning("Remote mode without token - tool calls may fail")
        executor = RemoteToolExecutor(args.backend, args.token)
    else:
        executor = LocalToolExecutor(args.sandbox)
    
    await executor.init()
    tools = executor.get_tools()
    
    if tools:
        logger.info(f"Available tools: {[t['name'] for t in tools]}")
    else:
        logger.warning("No tools available")
    
    # Create agent config
    config = AgentConfig(
        llm_url=args.llm,
        model=args.model,
        mcp_urls=[],  # We handle tools ourselves
        max_steps=args.max_steps,
    )
    
    agent = Agent(config)
    agent.tools = [type('Tool', (), t)() for t in tools]  # Convert to objects
    agent.tool_executor = executor  # Inject our executor
    
    try:
        logger.info(f"Running agent: {goal[:80]}...")
        result = await agent.run(goal)
        return result
    finally:
        await agent.close()
        if hasattr(executor, 'close'):
            await executor.close()


def interactive_mode(args):
    """Run agent in interactive mode."""
    mode = "remote" if args.remote else "local"
    print(f"\n🚀 BeyondCloud Agent - Interactive Mode ({mode})")
    print("=" * 50)
    print(f"LLM: {args.llm}")
    print(f"Model: {args.model}")
    if args.remote:
        print(f"Backend: {args.backend}")
    else:
        print(f"Sandbox: {args.sandbox}")
    print("=" * 50)
    print("Type your goal and press Enter. Type 'exit' to quit.\n")
    
    while True:
        try:
            goal = input("🎯 Goal: ").strip()
            
            if goal.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break
            
            if not goal:
                continue
            
            result = asyncio.run(run_agent(goal, args))
            print(f"\n📤 Result:\n{result}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Interactive mode
    if args.interactive or not args.goal:
        interactive_mode(args)
        return
    
    # Single goal mode
    try:
        result = asyncio.run(run_agent(args.goal, args))
        print(result)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
