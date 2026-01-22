"""
LLM Gateway Router - Unified chat completion endpoint

Provides:
- POST /api/llm/chat - Streaming chat completions via SSE
- OpenAI-compatible request/response format
- Centralized provider management
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

from app.services.provider_service import provider_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["LLM Gateway"])


class ChatMessage(BaseModel):
    """OpenAI-compatible chat message"""
    role: str
    content: str


class ToolFunction(BaseModel):
    """Tool function definition"""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class Tool(BaseModel):
    """Tool definition for function calling"""
    type: str = "function"
    function: ToolFunction


class ChatRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    provider: Optional[str] = None  # BeyondCloud extension
    tools: Optional[List[Tool]] = None
    # Pass-through parameters
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    reasoning_format: Optional[str] = None


@router.post("/chat")
async def chat_completion(request: ChatRequest):
    """
    POST /api/llm/chat
    
    Unified chat completion endpoint supporting streaming.
    Compatible with OpenAI API format.
    
    Streams SSE events in OpenAI format:
    - data: {"choices":[{"delta":{"content":"..."}}]}
    - data: [DONE]
    """
    # Convert messages to dict format
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Build extra params from optional fields
    extra_params = {}
    if request.top_p is not None:
        extra_params["top_p"] = request.top_p
    if request.top_k is not None:
        extra_params["top_k"] = request.top_k
    if request.frequency_penalty is not None:
        extra_params["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        extra_params["presence_penalty"] = request.presence_penalty
    if request.reasoning_format is not None:
        extra_params["reasoning_format"] = request.reasoning_format
    
    # Convert tools if provided
    tools = None
    if request.tools:
        tools = [t.model_dump() for t in request.tools]
    
    if request.stream:
        # Streaming response
        return StreamingResponse(
            provider_service.chat_completion_stream(
                messages=messages,
                model=request.model,
                provider_id=request.provider,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 1024,
                tools=tools,
                **extra_params
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    else:
        # Non-streaming response
        result = await provider_service.chat_completion(
            messages=messages,
            model=request.model,
            provider_id=request.provider,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1024,
            tools=tools,
        )
        
        # Format as OpenAI-compatible response
        return {
            "id": "chatcmpl-gateway",
            "object": "chat.completion",
            "model": result.get("model", request.model or "unknown"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("content", ""),
                    "tool_calls": result.get("tool_calls", None),
                },
                "finish_reason": "stop" if not result.get("error") else "error",
            }],
            "usage": result.get("usage", {}),
        }


@router.get("/status")
async def gateway_status():
    """
    GET /api/llm/status
    
    Returns the status of the LLM gateway and configured providers.
    """
    providers = await provider_service.list_providers()
    return {
        "status": "ok",
        "gateway": "python",
        "default_provider": provider_service.settings.default_llm_provider,
        "providers": [p.id for p in providers],
    }
