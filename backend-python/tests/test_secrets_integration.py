
import os
import pytest
from app.config import get_settings
from app.secrets import get_secret_manager_instance, EnvSecretManager

def test_secret_loading_from_env():
    # Force EnvSecretManager
    os.environ["SECRET_BACKEND"] = "env"
    os.environ["JWT_SECRET"] = "test-secret-123"
    
    # Reload settings
    from app.config import Settings
    settings = Settings()
    
    assert settings.jwt_secret == "test-secret-123"
    print("✅ Secret loading from env verified")

if __name__ == "__main__":
    test_secret_loading_from_env()
