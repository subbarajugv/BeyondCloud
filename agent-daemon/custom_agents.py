"""
Custom Agent Template

Examples showing how to create specialized agents by extending the base Agent class.
"""

from agent import Agent, AgentConfig


# ========== Example 1: Coding Agent ==========

class CodingAgent(Agent):
    """An agent specialized for coding tasks"""
    
    def __init__(self, sandbox_path: str = "/tmp/sandbox"):
        super().__init__(AgentConfig(
            system_prompt="""You are an expert coding assistant. You have access to tools for:
- Reading and writing files
- Running commands
- Searching code

Always:
1. Understand the task first
2. Plan your approach
3. Write clean, documented code
4. Test your changes
""",
            max_steps=20,
            mcp_urls=["http://localhost:8001/api/mcp"]
        ))
        self.sandbox_path = sandbox_path


# ========== Example 2: Research Agent ==========

class ResearchAgent(Agent):
    """An agent specialized for research and information gathering"""
    
    def __init__(self):
        super().__init__(AgentConfig(
            system_prompt="""You are a research assistant. You can:
- Search the web for information
- Take screenshots of web pages
- Analyze and summarize findings

Always cite your sources and provide balanced perspectives.
""",
            max_steps=15,
            mcp_urls=["http://localhost:8001/api/mcp"]
        ))
    
    async def run(self, goal: str) -> str:
        """Research with structured output"""
        # Enhance goal with research structure
        enhanced_goal = f"""Research Task: {goal}

Please provide:
1. Key findings
2. Sources used
3. Summary
"""
        return await super().run(enhanced_goal)


# ========== Example 3: Data Agent ==========

class DataAgent(Agent):
    """An agent for data analysis tasks"""
    
    def __init__(self):
        super().__init__(AgentConfig(
            system_prompt="""You are a data analyst. You can:
- Execute Python code for data analysis
- Query databases (read-only)
- Write results to files

Always validate data before analysis.
""",
            max_steps=10,
            mcp_urls=["http://localhost:8001/api/mcp"]
        ))


# ========== Example 4: Planning Agent ==========

class PlanningAgent(Agent):
    """An agent that focuses on planning before acting"""
    
    def __init__(self):
        super().__init__(AgentConfig(
            system_prompt="""You are a planning assistant. Before any action:
1. Use the 'think' tool to reason about the problem
2. Use the 'plan_task' tool to create a structured plan
3. Then execute the plan step by step

Always think before acting.
""",
            max_steps=25,
            mcp_urls=["http://localhost:8001/api/mcp"]
        ))


# ========== Usage Example ==========

async def main():
    """Example usage of custom agents"""
    
    # Create a coding agent
    agent = CodingAgent(sandbox_path="/tmp/my-project")
    
    # Discover available tools
    tools = await agent.discover_tools()
    print(f"Discovered {len(tools)} tools")
    
    # Run the agent
    result = await agent.run("Create a Python script that prints hello world")
    print(f"Result: {result}")
    
    # Cleanup
    await agent.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
