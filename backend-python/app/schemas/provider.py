"""
Provider types for Multi-Backend LLM Integration
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Provider(BaseModel):
    """LLM Provider configuration"""
    id: str
    name: str
    base_url: str
    has_api_key: bool
    is_default: bool
    models: List[str] = []


class ProviderConfig(BaseModel):
    """Runtime provider configuration"""
    id: str
    base_url: str
    api_key: Optional[str] = None
    default_model: Optional[str] = None


class LLMMessage(BaseModel):
    """Chat message"""
    role: str  # 'system', 'user', 'assistant'
    content: str


class LLMRequest(BaseModel):
    """LLM completion request"""
    messages: List[LLMMessage]
    model: Optional[str] = None
    provider: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class LLMChoice(BaseModel):
    """LLM response choice"""
    message: Optional[Dict[str, str]] = None
    delta: Optional[Dict[str, str]] = None
    index: int = 0
    finish_reason: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM completion response"""
    choices: List[LLMChoice]
    model: str
    usage: Optional[Dict[str, int]] = None


class ProviderTestResult(BaseModel):
    """Provider test result"""
    success: bool
    models: Optional[List[str]] = None
    error: Optional[str] = None


# Default provider configurations
DEFAULT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "llama.cpp": {
        "id": "llama.cpp",
        "name": "llama.cpp (Local)",
        "base_url": "http://localhost:8080/v1",
        "has_api_key": False,
        "is_default": True,
    },
    "ollama": {
        "id": "ollama",
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "has_api_key": False,
        "is_default": False,
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "has_api_key": True,
        "is_default": False,
    },
    "gemini": {
        "id": "gemini",
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "has_api_key": True,
        "is_default": False,
    },
    "groq": {
        "id": "groq",
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "has_api_key": True,
        "is_default": False,
    },
}
