#!/usr/bin/env python3
"""
BeyondCloud Agent Daemon

HTTP API that exposes the Agent for running agentic tasks.
The Agent discovers tools from MCP servers and runs an agentic loop.
"""

import os
import sys
import logging
import argparse
from typing import Optional, List
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install fastapi uvicorn pydantic httpx")
    sys.exit(1)

from agent import Agent, AgentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-daemon")

# ========== Configuration ==========

DEFAULT_PORT = 8002
VERSION = "4.0.0"

# CORS origins
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else DEFAULT_CORS_ORIGINS

# ========== API Models ==========

class RunAgentRequest(BaseModel):
    goal: str
    llm_url: Optional[str] = "http://localhost:8080/v1"
    mcp_urls: Optional[List[str]] = ["http://localhost:8001/api/mcp"]
    max_steps: Optional[int] = 10
    system_prompt: Optional[str] = None

class RunAgentResponse(BaseModel):
    result: str
    steps_taken: int
    tools_discovered: int
    status: str

class DiscoverToolsRequest(BaseModel):
    mcp_urls: List[str]

class ToolInfo(BaseModel):
    name: str
    description: str
    source: str

class DiscoverToolsResponse(BaseModel):
    tools: List[ToolInfo]
    count: int

# ========== Global Agent ==========

agent: Optional[Agent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = Agent()
    yield
    if agent:
        await agent.close()

# ========== FastAPI App ==========

app = FastAPI(
    title="BeyondCloud Agent",
    version=VERSION,
    description="Agent with LLM + Tool Discovery + Agentic Loop",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": "BeyondCloud Agent",
        "version": VERSION,
        "status": "running",
        "tools_discovered": len(agent.tools) if agent else 0
    }

@app.get("/api/agent/status")
def get_status():
    return {
        "version": VERSION,
        "tools_discovered": len(agent.tools) if agent else 0,
        "tool_sources": list(set(agent.tool_sources.values())) if agent else []
    }

@app.post("/api/agent/discover", response_model=DiscoverToolsResponse)
async def discover_tools(request: DiscoverToolsRequest):
    """Discover tools from MCP servers"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    tools = await agent.discover_tools(request.mcp_urls)
    
    return DiscoverToolsResponse(
        tools=[
            ToolInfo(
                name=t.name,
                description=t.description,
                source=agent.tool_sources.get(t.name, "")
            )
            for t in tools
        ],
        count=len(tools)
    )

@app.post("/api/agent/run", response_model=RunAgentResponse)
async def run_agent(request: RunAgentRequest):
    """Run the agent with a goal"""
    global agent
    
    # Create agent with request config
    config = AgentConfig(
        llm_url=request.llm_url,
        mcp_urls=request.mcp_urls,
        max_steps=request.max_steps,
        system_prompt=request.system_prompt or AgentConfig.system_prompt
    )
    
    run_agent = Agent(config)
    
    try:
        # Discover tools
        await run_agent.discover_tools()
        tools_count = len(run_agent.tools)
        
        # Run agentic loop
        result = await run_agent.run(request.goal)
        steps = len([m for m in run_agent.messages if m.role == "assistant"])
        
        return RunAgentResponse(
            result=result,
            steps_taken=steps,
            tools_discovered=tools_count,
            status="success"
        )
    except Exception as e:
        logger.exception(f"Agent run failed: {e}")
        return RunAgentResponse(
            result=str(e),
            steps_taken=0,
            tools_discovered=0,
            status="error"
        )
    finally:
        await run_agent.close()

@app.get("/api/agent/tools")
async def list_tools():
    """List discovered tools"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "source": agent.tool_sources.get(t.name, "")
            }
            for t in agent.tools
        ],
        "count": len(agent.tools)
    }

# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(description="BeyondCloud Agent Daemon")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print(f"🤖 Agent Daemon v{VERSION} on port {args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
