import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, ValidationInfo

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "DocuFlow AI Agent OS"
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "docuflow_super_secret_enterprise_agent_os_key_2026_safe"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI Provider
    AI_PROVIDER: str = "google_gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./docuflow.db"

    # Storage
    STORAGE_PATH: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # Agent Runtime Policy
    MAX_AGENT_TURNS: int = 15
    TOOL_EXECUTION_TIMEOUT_SECONDS: int = 45
    REQUIRE_APPROVAL_FOR_WRITES: bool = True
    APPROVAL_EXPIRY_HOURS: int = 24

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_credentials(cls, v: str, info: ValidationInfo) -> str:
        provider = info.data.get("AI_PROVIDER", "google_gemini")
        if provider == "google_gemini" and not v:
            raise ValueError(
                "GEMINI_API_KEY is required when AI_PROVIDER is 'google_gemini'. "
                "Please set GEMINI_API_KEY in your environment or .env file."
            )
        return v

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()

