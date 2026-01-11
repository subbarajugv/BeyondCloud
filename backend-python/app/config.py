"""
Configuration settings for the Python backend
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
