"""
Embedding Service - Multi-provider embedding abstraction

Supports:
- SentenceTransformers (local HuggingFace models)
- OpenAI Embeddings API
- Ollama Embeddings API

Usage:
    from app.services.embedding_service import embedding_service
    
    embeddings = await embedding_service.embed(["Hello world", "Test text"])
"""

from enum import Enum
from typing import Optional
import os
from abc import ABC, abstractmethod

from app.tracing import create_span


class EmbeddingProvider(str, Enum):
    """Supported embedding providers"""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    OLLAMA = "ollama"


# Model registry with dimensions
EMBEDDING_MODELS = {
    "sentence_transformers": {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "thenlper/gte-small": 384,
        "thenlper/gte-base": 768,
    },
    "openai": {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    },
    "ollama": {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
    },
}


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers"""
    
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding dimension for the current model"""
        pass


class SentenceTransformersEmbedder(BaseEmbedder):
    """Local embedding using sentence-transformers library"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with create_span("embedding.sentence_transformers", {
            "model": self.model_name,
            "text_count": len(texts)
        }):
            model = self._load_model()
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
    
    def get_dimension(self) -> int:
        return EMBEDDING_MODELS.get("sentence_transformers", {}).get(
            self.model_name, 384
        )


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI Embeddings API"""
    
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
        return self._client
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with create_span("embedding.openai", {
            "model": self.model_name,
            "text_count": len(texts)
        }):
            client = self._get_client()
            
            # OpenAI API call (sync, but generally fast)
            response = client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            
            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]
            return embeddings
    
    def get_dimension(self) -> int:
        return EMBEDDING_MODELS.get("openai", {}).get(
            self.model_name, 1536
        )


class OllamaEmbedder(BaseEmbedder):
    """Ollama Embeddings API"""
    
    def __init__(
        self, 
        model_name: str = "nomic-embed-text",
        base_url: Optional[str] = None
    ):
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        
        async with create_span("embedding.ollama", {
            "model": self.model_name,
            "text_count": len(texts)
        }):
            embeddings = []
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                for text in texts:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": self.model_name,
                            "prompt": text
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    embeddings.append(data["embedding"])
            
            return embeddings
    
    def get_dimension(self) -> int:
        return EMBEDDING_MODELS.get("ollama", {}).get(
            self.model_name, 768
        )


class EmbeddingService:
    """
    Unified embedding service with multi-provider support.
    
    Configuration via environment or settings:
    - EMBEDDING_PROVIDER: sentence_transformers | openai | ollama
    - EMBEDDING_MODEL: model name for the provider
    - OPENAI_API_KEY: required for OpenAI
    - OLLAMA_BASE_URL: optional, defaults to localhost:11434
    """
    
    def __init__(self):
        self._embedder: Optional[BaseEmbedder] = None
        self._current_provider: Optional[str] = None
        self._current_model: Optional[str] = None
    
    def configure(
        self,
        provider: str = "sentence_transformers",
        model: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Configure the embedding provider and model.
        
        Args:
            provider: One of 'sentence_transformers', 'openai', 'ollama'
            model: Model name (uses default for provider if not specified)
            **kwargs: Provider-specific options (api_key, base_url, etc.)
        """
        # Set defaults per provider
        default_models = {
            "sentence_transformers": "all-MiniLM-L6-v2",
            "openai": "text-embedding-3-small",
            "ollama": "nomic-embed-text",
        }
        
        model = model or default_models.get(provider, "all-MiniLM-L6-v2")
        
        # Only recreate if changed
        if self._current_provider == provider and self._current_model == model:
            return
        
        self._current_provider = provider
        self._current_model = model
        
        # Create appropriate embedder
        if provider == EmbeddingProvider.SENTENCE_TRANSFORMERS or provider == "sentence_transformers":
            self._embedder = SentenceTransformersEmbedder(model)
        elif provider == EmbeddingProvider.OPENAI or provider == "openai":
            self._embedder = OpenAIEmbedder(
                model, 
                api_key=kwargs.get("api_key")
            )
        elif provider == EmbeddingProvider.OLLAMA or provider == "ollama":
            self._embedder = OllamaEmbedder(
                model,
                base_url=kwargs.get("base_url")
            )
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
    
    def _ensure_configured(self):
        """Ensure service is configured with defaults if not explicitly configured"""
        if self._embedder is None:
            # Use environment variables or defaults
            provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
            model = os.getenv("EMBEDDING_MODEL")
            self.configure(provider=provider, model=model)
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts using configured provider.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            List of embedding vectors
        """
        self._ensure_configured()
        return await self._embedder.embed(texts)
    
    def get_dimension(self) -> int:
        """Get the embedding dimension for the current model"""
        self._ensure_configured()
        return self._embedder.get_dimension()
    
    def get_current_config(self) -> dict:
        """Get current configuration"""
        return {
            "provider": self._current_provider,
            "model": self._current_model,
            "dimension": self.get_dimension() if self._embedder else None,
        }
    
    @staticmethod
    def list_models(provider: Optional[str] = None) -> dict:
        """
        List available models by provider.
        
        Args:
            provider: Filter by provider (optional)
            
        Returns:
            Dict of provider -> {model: dimension}
        """
        if provider:
            return {provider: EMBEDDING_MODELS.get(provider, {})}
        return EMBEDDING_MODELS


# Global singleton instance
embedding_service = EmbeddingService()
