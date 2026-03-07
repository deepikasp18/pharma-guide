"""
Configuration settings for PharmaGuide application
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Application settings"""
    
    model_config = ConfigDict(env_file=".env")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Feature Flags
    USE_MOCK_SERVICES: bool = os.getenv("USE_MOCK_SERVICES", "true").lower() == "true"
    USE_REAL_LOGIC: bool = os.getenv("USE_REAL_LOGIC", "true").lower() == "true"  # Use real NLP/reasoning logic
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Neptune Configuration
    NEPTUNE_ENDPOINT: Optional[str] = os.getenv("NEPTUNE_ENDPOINT")
    NEPTUNE_PORT: int = int(os.getenv("NEPTUNE_PORT", "8182"))
    
    # OpenSearch Configuration
    OPENSEARCH_HOST: str = os.getenv("OPENSEARCH_HOST", "localhost")
    OPENSEARCH_PORT: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")

settings = Settings()