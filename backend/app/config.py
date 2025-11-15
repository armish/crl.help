"""
Configuration management for FDA CRL Explorer.
Uses Pydantic Settings for environment variable validation and type safety.
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    Required settings will raise ValidationError if not provided.
    """

    # OpenAI API Configuration
    openai_api_key: str = Field(
        default="sk-dummy-key-for-dry-run-mode",
        description="OpenAI API key for summarization and embeddings. Not required in dry-run mode."
    )

    # Database Configuration
    database_path: str = Field(
        default="./data/crl_explorer.duckdb",
        description="Path to DuckDB database file"
    )

    # FDA API Configuration
    fda_json_url: str = Field(
        default="https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip",
        description="URL for CRL JSON data bulk download"
    )

    # Data storage paths
    data_raw_dir: str = Field(
        default="./data/raw",
        description="Directory for raw downloaded data"
    )

    data_processed_dir: str = Field(
        default="./data/processed",
        description="Directory for processed data"
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
        default="gpt-5-nano",
        description="OpenAI model for summarization"
    )

    openai_embedding_model: str = Field(
        default="text-embedding-3-large",
        description="OpenAI model for embeddings (text-embedding-3-large: 64.6% MTEB, 3072 dims)"
    )

    openai_qa_model: str = Field(
        default="gpt-5-nano",
        description="OpenAI model for Q&A"
    )

    # AI Service Configuration
    ai_dry_run: bool = Field(
        default=False,
        description="Enable dry-run mode: generate dummy summaries without API calls (saves costs)"
    )

    ai_dry_run_summary_chars: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="Number of characters to use for dummy summaries in dry-run mode"
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

    @model_validator(mode='after')
    def validate_openai_api_key(self) -> 'Settings':
        """Validate OpenAI API key format after all fields are set."""
        # Skip validation if in dry-run mode
        if self.ai_dry_run:
            return self

        if len(self.openai_api_key) < 20:
            raise ValueError(
                "openai_api_key must be at least 20 characters. "
                "Please provide a valid OpenAI API key or enable AI_DRY_RUN mode."
            )

        if not self.openai_api_key.startswith("sk-"):
            raise ValueError(
                "openai_api_key must start with 'sk-'. "
                "Please provide a valid OpenAI API key or enable AI_DRY_RUN mode."
            )
        return self

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


# Create a global settings instance for easy access
settings = get_settings()
