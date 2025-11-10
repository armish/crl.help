"""
Configuration management for FDA CRL Explorer.
Uses Pydantic Settings for environment variable validation and type safety.
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    Required settings will raise ValidationError if not provided.
    """

    # OpenAI API Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for summarization and embeddings. REQUIRED.",
        min_length=20
    )

    # Database Configuration
    database_path: str = Field(
        default="./data/crl_explorer.duckdb",
        description="Path to DuckDB database file"
    )

    # FDA API Configuration
    fda_bulk_approved_url: str = Field(
        default="https://download.open.fda.gov/approved_CRLs.zip",
        description="URL for approved CRLs bulk download"
    )

    fda_bulk_unapproved_url: str = Field(
        default="https://download.open.fda.gov/unapproved_CRLs.zip",
        description="URL for unapproved CRLs bulk download"
    )

    # Scheduled Task Configuration
    schedule_hour: int = Field(
        default=2,
        ge=0,
        le=23,
        description="Hour of day (0-23) to run daily data pipeline"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # Application Configuration
    app_name: str = Field(
        default="FDA CRL Explorer",
        description="Application name"
    )

    app_version: str = Field(
        default="0.1.0",
        description="Application version"
    )

    # API Configuration
    api_prefix: str = Field(
        default="/api",
        description="API route prefix"
    )

    # OpenAI Model Configuration
    openai_summary_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model for summarization"
    )

    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model for embeddings"
    )

    openai_qa_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model for Q&A"
    )

    # RAG Configuration
    rag_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top similar CRLs to retrieve for RAG"
    )

    # Model configuration for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(
                f"log_level must be one of {allowed_levels}, got '{v}'"
            )
        return v_upper

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        """Validate OpenAI API key format."""
        if not v.startswith("sk-"):
            raise ValueError(
                "openai_api_key must start with 'sk-'. "
                "Please provide a valid OpenAI API key."
            )
        return v

    def get_cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function uses lru_cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.

    Returns:
        Settings: Application settings instance

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()
