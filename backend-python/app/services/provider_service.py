"""
Provider Service - Manages LLM provider configuration and testing

TODO: Implement the following methods matching the Node.js implementation
"""
from typing import List, Optional, Dict
import httpx
from ..config import get_settings
from ..schemas.provider import (
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


# Singleton instance
provider_service = ProviderService()
