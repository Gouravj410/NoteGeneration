import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "StudyForge AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="SUPER_SECRET_STUDY_FORGE_KEY_CHANGE_ME_IN_PRODUCTION", description="JWT Signing Key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/studyforge", description="PostgreSQL DB URL")
    
    # Redis & Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis DB URL")
    
    # File Storage
    STORAGE_DIR: str = Field(default="storage", description="Local directory for storage in dev")
    S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    
    # Default Models
    DEFAULT_LLM_PROVIDER: str = "openai"  # openai or gemini
    DEFAULT_STRONG_MODEL: str = "gpt-4o"  # or gemini-1.5-pro
    DEFAULT_CHEAP_MODEL: str = "gpt-4o-mini"  # or gemini-1.5-flash
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # OCR
    TESSERACT_CMD: Optional[str] = None  # Windows path to tesseract.exe if needed
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure local storage directory exists
if not settings.S3_BUCKET and not os.path.exists(settings.STORAGE_DIR):
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
