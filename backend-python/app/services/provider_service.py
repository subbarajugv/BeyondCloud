"""
Provider Service - Manages LLM provider configuration and testing

Implements:
- Provider configuration management
- Retry logic with exponential backoff for API resilience
- Chat completion with tool support
"""
from typing import List, Optional, Dict, AsyncGenerator, Any
import httpx
import asyncio
import logging
from functools import wraps
from app.config import get_settings

logger = logging.getLogger(__name__)


# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 30.0  # seconds
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def with_retry(max_retries: int = MAX_RETRIES):
    """
    Decorator for async functions that adds exponential backoff retry logic.
    
    Retries on:
    - Connection errors
    - Timeout errors  
    - HTTP 429/5xx status codes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            backoff = INITIAL_BACKOFF
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code not in RETRYABLE_STATUS_CODES:
                        raise
                    last_exception = e
                    logger.warning(
                        f"Retryable HTTP error {e.response.status_code} on attempt {attempt + 1}/{max_retries + 1}"
                    )
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    last_exception = e
                    logger.warning(
                        f"Connection/timeout error on attempt {attempt + 1}/{max_retries + 1}: {e}"
                    )
                
                if attempt < max_retries:
                    sleep_time = min(backoff, MAX_BACKOFF)
                    logger.info(f"Retrying in {sleep_time:.1f}s...")
                    await asyncio.sleep(sleep_time)
                    backoff *= BACKOFF_MULTIPLIER
            
            raise last_exception
        return wrapper
    return decorator
from app.schemas.provider import (
    Provider,
    ProviderConfig,
    ProviderTestResult,
    DEFAULT_PROVIDERS,
)


class ProviderService:
    """Manages LLM provider configuration and testing"""
    
    def __init__(self):
        self.settings = get_settings()
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize providers from environment config"""
        provider_config = self.settings.get_provider_config()
        
        for provider_id, config in provider_config.items():
            self.provider_configs[provider_id] = ProviderConfig(
                id=provider_id,
                base_url=config["base_url"],
                api_key=config.get("api_key"),
            )
    
    async def list_providers(self) -> List[Provider]:
        """
        List all available providers with their current status
        
        Returns:
            List of Provider objects with configuration details
        """
        providers: List[Provider] = []
        
        for provider_id, defaults in DEFAULT_PROVIDERS.items():
            runtime_config = self.provider_configs.get(provider_id)
            
            providers.append(Provider(
                id=defaults["id"],
                name=defaults["name"],
                base_url=runtime_config.base_url if runtime_config else defaults["base_url"],
                has_api_key=bool(runtime_config.api_key) if defaults["has_api_key"] else False,
                is_default=provider_id == self.settings.default_llm_provider,
                models=[],  # Populated when fetched
            ))
        
        return providers
    
    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get a specific provider configuration"""
        return self.provider_configs.get(provider_id)
    
    async def test_provider(
        self, 
        provider_id: str, 
        api_key: Optional[str] = None
    ) -> ProviderTestResult:
        """
        Test connection to a provider and fetch available models
        
        Args:
            provider_id: ID of the provider to test
            api_key: Optional API key to use for testing
            
        Returns:
            ProviderTestResult with success status and models or error
        """
        defaults = DEFAULT_PROVIDERS.get(provider_id)
        if not defaults:
            return ProviderTestResult(
                success=False,
                error=f"Unknown provider: {provider_id}"
            )
        
        runtime_config = self.provider_configs.get(provider_id)
        base_url = runtime_config.base_url if runtime_config else defaults["base_url"]
        key = api_key or (runtime_config.api_key if runtime_config else None)
        
        # Check if API key is required but not provided
        if defaults["has_api_key"] and not key:
            return ProviderTestResult(
                success=False,
                error="API key required for this provider"
            )
        
        try:
            models = await self.fetch_models(base_url, key)
            return ProviderTestResult(success=True, models=models)
        except Exception as e:
            return ProviderTestResult(success=False, error=str(e))
    
    async def fetch_models(
        self, 
        base_url: str, 
        api_key: Optional[str] = None
    ) -> List[str]:
        """
        Fetch models from a provider
        
        Args:
            base_url: Provider API base URL
            api_key: Optional API key for authentication
            
        Returns:
            List of model IDs/names
        """
        headers = {"Content-Type": "application/json"}
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            return [m.get("id") or m.get("name") or str(m) for m in data]
        elif "data" in data and isinstance(data["data"], list):
            return [m.get("id") or m.get("name") or str(m) for m in data["data"]]
        elif "models" in data and isinstance(data["models"], list):
            return [m.get("id") or m.get("name") or str(m) for m in data["models"]]
        
        return ["default"]
    
    async def get_models(self, provider_id: str) -> List[str]:
        """Get models for a specific provider"""
        result = await self.test_provider(provider_id)
        return result.models if result.success and result.models else []
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Send chat completion request to LLM provider
        """
        # Get provider configuration
        pid = provider_id or self.settings.default_llm_provider
        runtime_config = self.provider_configs.get(pid)
        defaults = DEFAULT_PROVIDERS.get(pid, {})
        
        if not runtime_config and not defaults:
            raise ValueError(f"Unknown provider: {pid}")
        
        base_url = runtime_config.base_url if runtime_config else defaults.get("base_url")
        api_key = runtime_config.api_key if runtime_config else None
        
        # Use first available model if not specified
        model_id = model
        if not model_id:
            models = defaults.get("models", [])
            model_id = models[0] if models else "default"
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            
            # Extract content from OpenAI-compatible response
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
                
                return {
                    "content": content,
                    "tool_calls": tool_calls,
                    "model": data.get("model", model_id),
                    "usage": data.get("usage", {}),
                }
            else:
                return {"content": "", "error": "No response from model"}
                
        except httpx.HTTPStatusError as e:
            return {"content": "", "error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"content": "", "error": str(e)}
    
    def update_provider(self, provider_id: str, **updates) -> None:
        """Update provider configuration"""
        existing = self.provider_configs.get(provider_id)
        if existing:
            for key, value in updates.items():
                setattr(existing, key, value)
        else:
            self.provider_configs[provider_id] = ProviderConfig(
                id=provider_id,
                **updates
            )
    
    async def chat_completion_stream(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        tools: Optional[List[Dict]] = None,
        **extra_params
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion response as SSE-formatted chunks.
        
        Yields:
            SSE-formatted strings ready to send to client
        """
        # Get provider configuration
        pid = provider_id or self.settings.default_llm_provider
        runtime_config = self.provider_configs.get(pid)
        defaults = DEFAULT_PROVIDERS.get(pid, {})
        
        if not runtime_config and not defaults:
            yield f'data: {{"error": "Unknown provider: {pid}"}}\n\n'
            return
        
        base_url = runtime_config.base_url if runtime_config else defaults.get("base_url")
        api_key = runtime_config.api_key if runtime_config else None
        
        # Use first available model if not specified
        model_id = model
        if not model_id:
            models = defaults.get("models", [])
            model_id = models[0] if models else "default"
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **extra_params
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f'data: {{"error": "HTTP {response.status_code}: {error_text.decode()}"}}\n\n'
                        return
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            # Pass through SSE data directly
                            yield f"{line}\n"
                        elif line == "":
                            # Empty line = end of SSE event
                            yield "\n"
        except httpx.ConnectError as e:
            logger.error(f"Connection error to LLM provider: {e}")
            yield f'data: {{"error": "Connection failed: {str(e)}"}}\n\n'
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to LLM provider: {e}")
            yield f'data: {{"error": "Request timeout"}}\n\n'
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f'data: {{"error": "{str(e)}"}}\n\n'


# Singleton instance
provider_service = ProviderService()
