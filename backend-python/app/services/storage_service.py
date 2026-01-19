"""
Storage Service - Hybrid S3-compatible storage for RAG files

Supports:
- LocalStorageBackend: Filesystem storage for development/testing
- S3StorageBackend: S3-compatible storage (AWS S3, MinIO) for production
"""
import os
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from app.config import get_settings


class StorageBackend(ABC):
    """Abstract storage interface"""
    
    @abstractmethod
    async def upload(self, content: bytes, filename: str, user_id: str) -> str:
        """Upload file, return storage key"""
        pass
    
    @abstractmethod
    async def download(self, storage_key: str) -> bytes:
        """Download file by storage key"""
        pass
    
    @abstractmethod
    async def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get URL (presigned for S3, file:// for local)"""
        pass
    
    @abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """Delete file"""
        pass
    
    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageBackend(StorageBackend):
    """Filesystem storage for development/testing"""
    
    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_full_path(self, storage_key: str) -> str:
        return os.path.join(self.base_path, storage_key)
    
    async def upload(self, content: bytes, filename: str, user_id: str) -> str:
        """Upload file to local filesystem"""
        # Create storage key: {user_id}/{uuid}_{filename}
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        storage_key = f"{user_id}/{uuid.uuid4().hex}_{safe_filename}"
        
        full_path = self._get_full_path(storage_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(content)
        
        return storage_key
    
    async def download(self, storage_key: str) -> bytes:
        """Download file from local filesystem"""
        full_path = self._get_full_path(storage_key)
        with open(full_path, "rb") as f:
            return f.read()
    
    async def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get file:// URL for local file"""
        return f"file://{self._get_full_path(storage_key)}"
    
    async def delete(self, storage_key: str) -> bool:
        """Delete file from local filesystem"""
        full_path = self._get_full_path(storage_key)
        if os.path.exists(full_path):
            os.remove(full_path)
            # Try to remove empty parent directories
            try:
                os.removedirs(os.path.dirname(full_path))
            except OSError:
                pass  # Directory not empty, that's fine
            return True
        return False
    
    async def exists(self, storage_key: str) -> bool:
        """Check if file exists locally"""
        return os.path.exists(self._get_full_path(storage_key))


class S3StorageBackend(StorageBackend):
    """S3-compatible storage (AWS S3, MinIO) for production"""
    
    def __init__(
        self,
        bucket: str,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1"
    ):
        import boto3
        from botocore.config import Config
        
        self.bucket = bucket
        
        # Configure client
        client_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}  # Required for MinIO
        )
        
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=client_config
        )
    
    async def upload(self, content: bytes, filename: str, user_id: str) -> str:
        """Upload file to S3"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        storage_key = f"{user_id}/{uuid.uuid4().hex}_{safe_filename}"
        
        self.client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=content
        )
        
        return storage_key
    
    async def download(self, storage_key: str) -> bytes:
        """Download file from S3"""
        response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        return response["Body"].read()
    
    async def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get presigned URL for S3 object"""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires_in
        )
    
    async def delete(self, storage_key: str) -> bool:
        """Delete file from S3"""
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)
        return True
    
    async def exists(self, storage_key: str) -> bool:
        """Check if object exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception:
            return False


def get_storage_backend() -> StorageBackend:
    """Factory function to get configured storage backend"""
    settings = get_settings()
    
    if settings.storage_type == "s3":
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_TYPE=s3")
        
        return S3StorageBackend(
            bucket=settings.s3_bucket,
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region
        )
    else:
        return LocalStorageBackend(settings.storage_local_path)


# Singleton instance - lazy loaded
_storage_service: Optional[StorageBackend] = None


def get_storage_service() -> StorageBackend:
    """Get the storage service singleton"""
    global _storage_service
    if _storage_service is None:
        _storage_service = get_storage_backend()
    return _storage_service
