"""
llama.cpp Auth WebUI - Python/FastAPI Backend
Phase 0: Multi-Backend LLM Integration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.config import get_settings
from app.routers import providers

settings = get_settings()

app = FastAPI(
    title="llama.cpp Auth WebUI API",
    description="Backend API for llama.cpp Authenticated WebUI",
    version="1.0.0",
)

# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
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
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Provider routes (Phase 0)
app.include_router(providers.router, prefix="/api")

# Models endpoint (convenience alias)
@app.get("/api/models")
async def get_models(provider: str = "llama.cpp"):
    """Get models for a provider (alias for /api/providers/models)"""
    from app.services.provider_service import provider_service
    models = await provider_service.get_models(provider)
    return {"models": models, "provider": provider}


# =============================================================================
# Placeholder routes for future phases
# =============================================================================

@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_placeholder(path: str):
    """Placeholder for auth endpoints (Phase 1)"""
    return {
        "error": {
            "code": "NOT_IMPLEMENTED",
            "message": "Authentication endpoints coming in Phase 1",
        }
    }


@app.post("/api/chat/completions")
async def chat_completions_placeholder():
    """Placeholder for chat completion (Phase 1)"""
    return {
        "error": {
            "code": "NOT_IMPLEMENTED",
            "message": "Chat completion endpoint coming in Phase 1",
        }
    }


# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
async def startup_event():
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦙 llama.cpp Auth WebUI - Backend (Python)              ║
║                                                           ║
║   Server running on http://localhost:{settings.port}               ║
║   Default LLM: {settings.default_llm_provider.ljust(11)}                           ║
║                                                           ║
║   Endpoints:                                              ║
║   - GET  /api/health                                      ║
║   - GET  /api/providers                                   ║
║   - POST /api/providers/test                              ║
║   - GET  /api/models                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
