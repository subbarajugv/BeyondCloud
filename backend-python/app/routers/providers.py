"""
Provider API Routes
Implements Phase 0 endpoints: GET /providers, POST /providers/test, GET /models
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.provider_service import provider_service


router = APIRouter(prefix="/providers", tags=["providers"])


class TestProviderRequest(BaseModel):
    """Request body for testing a provider"""
    id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class TestProviderResponse(BaseModel):
    """Response for provider test"""
    success: bool
    models: Optional[list] = None


class ModelsResponse(BaseModel):
    """Response for models endpoint"""
    models: list
    provider: str


@router.get("")
async def list_providers():
    """
    GET /api/providers
    List all available LLM providers
    """
    providers = await provider_service.list_providers()
    return {"providers": [p.model_dump() for p in providers]}


@router.post("/test")
async def test_provider(request: TestProviderRequest):
    """
    POST /api/providers/test
    Test connection to a provider
    """
    # If custom baseUrl provided, update temporarily
    if request.base_url:
        provider_service.update_provider(request.id, base_url=request.base_url)
    
    result = await provider_service.test_provider(request.id, request.api_key)
    
    if result.success:
        return {"success": True, "models": result.models}
    else:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_ERROR",
                "message": result.error or "Provider connection failed",
            }
        )


@router.get("/models")
async def get_models(provider: str = "llama.cpp"):
    """
    GET /api/models
    Get available models for a provider
    """
    models = await provider_service.get_models(provider)
    return {"models": models, "provider": provider}
