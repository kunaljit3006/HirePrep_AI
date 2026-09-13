import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "HirePrep_AI Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hireprep.db"

    # LLM Providers (Open Source & Free-tier)
    GROQ_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Coding profiles & External APIs
    GITHUB_TOKEN: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Supabase Auth
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    AUTH_ENABLED: bool = True

    # Azure AI Speech (TTS)
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = "eastus"
    AZURE_SPEECH_VOICE: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            ".env",
            "backend/.env"
        ),
        extra="ignore"
    )

settings = Settings()
