"""
Configuration settings for the Python backend

Enterprise Secrets Management:
    Set SECRET_BACKEND environment variable:
    - "env" (default): Use .env files (development only)
    - "vault": HashiCorp Vault (production)
    - "aws": AWS Secrets Manager (production)
    
    See app/secrets.py for implementation details.
"""
import os
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment"""
    
    # Server
    port: int = 3000
    debug: bool = True
    
    # Database (Phase 1)
    database_url: str = "postgresql+asyncpg://localhost:5432/llamacpp_chat"
    
    # JWT (Phase 1)
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:5173"
    
    # LLM Providers
    default_llm_provider: str = "llama.cpp"
    
    # Provider URLs
    llama_cpp_url: str = "http://localhost:8080/v1"
    ollama_url: str = "http://localhost:11434/v1"
    openai_url: str = "https://api.openai.com/v1"
    gemini_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    groq_url: str = "https://api.groq.com/openai/v1"
    
    # API Keys (optional)
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    
    # RAG Settings
    embedding_model: str = "all-MiniLM-L6-v2"  # 384 dims, fast, good quality
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Fast cross-encoder
    embedding_dimension: int = 384  # Must match the embedding model output
    
    # Storage Settings (local for dev, s3 for production)
    storage_type: str = "local"  # "local" or "s3"
    storage_local_path: str = "./storage"  # For local storage
    s3_bucket: Optional[str] = None
    s3_endpoint: Optional[str] = None  # MinIO: http://localhost:9000
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_region: str = "us-east-1"
    
    def __init__(self, **values: Any):
        super().__init__(**values)
        self._load_enterprise_secrets()

    def _load_enterprise_secrets(self):
        """
        Dynamically load sensitive settings from the configured SecretManager.
        This overrides values from .env or environment variables if found in
        the secure backend (Vault, AWS).
        """
        from app.secrets import get_secret_sync
        
        # List of sensitive keys to attempt loading
        sensitive_keys = [
            "DATABASE_URL", "JWT_SECRET", 
            "OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
            "S3_ACCESS_KEY", "S3_SECRET_KEY"
        ]
        
        for key in sensitive_keys:
            secret = get_secret_sync(key)
            if secret:
                attr_name = key.lower()
                if hasattr(self, attr_name):
                    setattr(self, attr_name, secret)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_provider_config(self) -> Dict[str, Dict[str, Any]]:
        """Get provider configurations from settings"""
        return {
            "llama.cpp": {
                "base_url": self.llama_cpp_url,
            },
            "ollama": {
                "base_url": self.ollama_url,
            },
            "openai": {
                "base_url": self.openai_url,
                "api_key": self.openai_api_key,
            },
            "gemini": {
                "base_url": self.gemini_url,
                "api_key": self.gemini_api_key,
            },
            "groq": {
                "base_url": self.groq_url,
                "api_key": self.groq_api_key,
            },
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
