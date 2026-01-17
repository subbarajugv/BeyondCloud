"""
BeyondCloud - Python/FastAPI Backend
Phase 0-4: Multi-Backend LLM + RAG + Tracing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.config import get_settings
from app.routers import providers
from app.routers import rag
from app.routers import query
from app.routers import agent
from app.routers import mcp
from app.database import init_database

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_database()
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🌐 BeyondCloud - Python AI Service                      ║
║                                                           ║
║   Server running on http://localhost:{settings.port}               ║
║   Default LLM: {settings.default_llm_provider.ljust(11)}                           ║
║                                                           ║
║   Phase 0 - Providers:                                    ║
║   - GET  /api/health                                      ║
║   - GET  /api/providers                                   ║
║   - POST /api/providers/test                              ║
║   - GET  /api/models                                      ║
║                                                           ║
║   Phase 4 - RAG:                                          ║
║   - GET  /api/rag/sources                                 ║
║   - POST /api/rag/ingest                                  ║
║   - POST /api/rag/ingest/file                             ║
║   - POST /api/rag/retrieve                                ║
║   - POST /api/rag/query                                   ║
║   - DELETE /api/rag/sources/:id                           ║
║                                                           ║
║   Phase 4 - Query Preprocessing:                          ║
║   - POST /api/query/process                               ║
║   - POST /api/query/confirm                               ║
║   - POST /api/query/process-and-retrieve                  ║
║                                                           ║
║   Phase 5 - Agentic Tools:                                ║
║   - POST /api/agent/set-sandbox                           ║
║   - POST /api/agent/set-mode                              ║
║   - POST /api/agent/execute                               ║
║   - POST /api/agent/approve/:id                           ║
║   - GET  /api/agent/status                                ║
║                                                           ║
║   Phase 6 - MCP Integration:                              ║
║   - GET  /api/mcp/servers                                 ║
║   - POST /api/mcp/servers                                 ║
║   - DELETE /api/mcp/servers/:id                           ║
║   - GET  /api/mcp/tools                                   ║
║   - POST /api/mcp/tools/call                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="BeyondCloud - AI Service",
    description="Python AI Service for RAG, Agents, and Memory",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],  # Allow Node.js backend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Routes
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "python-ai",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Provider routes (Phase 0)
app.include_router(providers.router, prefix="/api")

# RAG routes (Phase 4)
app.include_router(rag.router, prefix="/api")

# Query preprocessing routes (Phase 4)
app.include_router(query.router, prefix="/api")

# Agent routes (Phase 5)
app.include_router(agent.router)

# MCP routes (Phase 6)
app.include_router(mcp.router)

# Models endpoint (convenience alias)
@app.get("/api/models")
async def get_models(provider: str = "llama.cpp"):
    """Get models for a provider (alias for /api/providers/models)"""
    from app.services.provider_service import provider_service
    models = await provider_service.get_models(provider)
    return {"models": models, "provider": provider}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
