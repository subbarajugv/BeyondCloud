"""
Secrets Manager - Enterprise-grade secret retrieval abstraction

Supports:
- EnvSecretManager: Local .env files (development)
- VaultSecretManager: HashiCorp Vault (production)
- AWSSecretManager: AWS Secrets Manager (production)

Usage:
    from app.secrets import get_secret_manager, secret_manager
    
    # Get a secret
    jwt_secret = await secret_manager.get_secret("JWT_SECRET")
    
    # Or use the async context
    async with get_secret_manager() as sm:
        db_password = await sm.get_secret("DATABASE_PASSWORD")
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class SecretManager(ABC):
    """Abstract base class for secret management backends"""
    
    @abstractmethod
    async def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret by key.
        
        Args:
            key: The secret key/name
            default: Default value if secret not found
            
        Returns:
            The secret value or default
        """
        pass
    
    @abstractmethod
    async def get_secrets(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets at once (batch operation)"""
        pass
    
    async def close(self):
        """Cleanup resources"""
        pass


class EnvSecretManager(SecretManager):
    """
    Environment-based secret manager for development.
    Reads from environment variables and .env files.
    
    WARNING: Not recommended for production - secrets in .env files
    can be accidentally committed or exposed.
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        logger.info("Using EnvSecretManager (development mode)")
    
    async def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment variable"""
        return os.getenv(key, default)
    
    async def get_secrets(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from environment"""
        return {key: os.getenv(key) for key in keys}


class VaultSecretManager(SecretManager):
    """
    HashiCorp Vault secret manager for production.
    
    Requires:
        pip install hvac
        
    Environment:
        VAULT_ADDR: Vault server address (e.g., https://vault.example.com:8200)
        VAULT_TOKEN: Authentication token (or use AppRole/K8s auth)
        VAULT_MOUNT: KV secrets engine mount point (default: "secret")
        VAULT_PATH: Path prefix for secrets (default: "beyondcloud")
    """
    
    def __init__(self):
        self._client = None
        self._mount = os.getenv("VAULT_MOUNT", "secret")
        self._path = os.getenv("VAULT_PATH", "beyondcloud")
        self._cache: Dict[str, str] = {}
        logger.info(f"Using VaultSecretManager (mount={self._mount}, path={self._path})")
    
    def _get_client(self):
        """Lazy initialization of Vault client"""
        if self._client is None:
            try:
                import hvac
            except ImportError:
                raise ImportError(
                    "hvac package required for Vault integration. "
                    "Install with: pip install hvac"
                )
            
            vault_addr = os.getenv("VAULT_ADDR")
            vault_token = os.getenv("VAULT_TOKEN")
            
            if not vault_addr:
                raise ValueError("VAULT_ADDR environment variable required")
            
            self._client = hvac.Client(url=vault_addr, token=vault_token)
            
            if not self._client.is_authenticated():
                raise ConnectionError("Failed to authenticate with Vault")
            
            logger.info(f"Connected to Vault at {vault_addr}")
        
        return self._client
    
    async def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from Vault KV store"""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        try:
            client = self._get_client()
            secret_path = f"{self._path}/{key}"
            
            # KV v2 read
            response = client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=self._mount
            )
            
            value = response["data"]["data"].get("value", default)
            self._cache[key] = value
            return value
            
        except Exception as e:
            logger.warning(f"Failed to get secret '{key}' from Vault: {e}")
            return default
    
    async def get_secrets(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from Vault"""
        results = {}
        for key in keys:
            results[key] = await self.get_secret(key)
        return results
    
    async def close(self):
        """Close Vault client connection"""
        if self._client:
            self._client = None


class AWSSecretManager(SecretManager):
    """
    AWS Secrets Manager for production.
    
    Requires:
        pip install boto3
        
    Environment:
        AWS_REGION: AWS region (default: us-east-1)
        AWS_SECRET_PREFIX: Prefix for secret names (default: "beyondcloud/")
        
    Authentication via standard AWS credentials chain:
        - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        - IAM role (recommended for EC2/ECS/Lambda)
        - AWS credentials file
    """
    
    def __init__(self):
        self._client = None
        self._region = os.getenv("AWS_REGION", "us-east-1")
        self._prefix = os.getenv("AWS_SECRET_PREFIX", "beyondcloud/")
        self._cache: Dict[str, str] = {}
        logger.info(f"Using AWSSecretManager (region={self._region}, prefix={self._prefix})")
    
    def _get_client(self):
        """Lazy initialization of AWS Secrets Manager client"""
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3 package required for AWS Secrets Manager. "
                    "Install with: pip install boto3"
                )
            
            self._client = boto3.client(
                "secretsmanager",
                region_name=self._region
            )
            logger.info(f"Connected to AWS Secrets Manager in {self._region}")
        
        return self._client
    
    async def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        try:
            import json
            client = self._get_client()
            secret_name = f"{self._prefix}{key}"
            
            response = client.get_secret_value(SecretId=secret_name)
            
            # Handle both string and JSON secrets
            if "SecretString" in response:
                secret_string = response["SecretString"]
                # Try to parse as JSON (AWS console often creates JSON secrets)
                try:
                    secret_data = json.loads(secret_string)
                    value = secret_data.get("value", secret_string)
                except json.JSONDecodeError:
                    value = secret_string
            else:
                # Binary secret
                import base64
                value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
            
            self._cache[key] = value
            return value
            
        except Exception as e:
            logger.warning(f"Failed to get secret '{key}' from AWS: {e}")
            return default
    
    async def get_secrets(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from AWS (uses batch get when possible)"""
        results = {}
        for key in keys:
            results[key] = await self.get_secret(key)
        return results
    
    async def close(self):
        """Cleanup AWS client"""
        self._client = None


# =============================================================================
# Factory and Global Instance
# =============================================================================

_secret_manager: Optional[SecretManager] = None


def get_secret_manager_instance() -> SecretManager:
    """
    Get or create the global secret manager instance.
    
    Backend selection via SECRET_BACKEND environment variable:
        - "env" (default): Environment variables
        - "vault": HashiCorp Vault
        - "aws": AWS Secrets Manager
    """
    global _secret_manager
    
    if _secret_manager is None:
        backend = os.getenv("SECRET_BACKEND", "env").lower()
        
        if backend == "vault":
            _secret_manager = VaultSecretManager()
        elif backend == "aws":
            _secret_manager = AWSSecretManager()
        else:
            _secret_manager = EnvSecretManager()
    
    return _secret_manager


async def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    manager = get_secret_manager_instance()
    return await manager.get_secret(key, default)


# Alias for common usage
secret_manager = get_secret_manager_instance
