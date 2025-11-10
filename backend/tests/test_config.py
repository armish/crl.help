"""
Unit tests for app/config.py

Tests configuration management, environment variable loading,
and validation of settings.
"""

import os
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""

    def test_settings_with_valid_env_vars(self, test_env_vars):
        """Test that settings load correctly with valid environment variables."""
        settings = get_settings()

        assert settings.openai_api_key == "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
        assert settings.database_path == ":memory:"
        assert settings.log_level == "DEBUG"
        assert settings.cors_origins == "http://localhost:3000,http://localhost:5173"

    def test_settings_defaults(self, test_env_vars):
        """Test that default values are set correctly."""
        settings = get_settings()

        assert settings.app_name == "FDA CRL Explorer"
        assert settings.app_version == "0.1.0"
        assert settings.api_prefix == "/api"
        assert settings.schedule_hour == 2
        assert settings.openai_summary_model == "gpt-4o-mini"
        assert settings.openai_embedding_model == "text-embedding-3-small"
        assert settings.openai_qa_model == "gpt-4o-mini"
        assert settings.rag_top_k == 5

    def test_openai_api_key_validation_missing(self, test_env_vars):
        """Test that missing OpenAI API key raises ValidationError."""
        # Remove the API key
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Restore the key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        get_settings.cache_clear()

        assert "openai_api_key" in str(exc_info.value)

    def test_openai_api_key_validation_invalid_format(self, test_env_vars):
        """Test that invalid OpenAI API key format raises ValidationError."""
        # Set invalid API key (doesn't start with 'sk-', but is long enough)
        os.environ["OPENAI_API_KEY"] = "invalid-key-format-1234567890"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "must start with 'sk-'" in str(exc_info.value)

        # Restore valid key
        os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
        get_settings.cache_clear()

    def test_openai_api_key_validation_too_short(self, test_env_vars):
        """Test that too-short OpenAI API key raises ValidationError."""
        # Set too-short API key
        os.environ["OPENAI_API_KEY"] = "sk-short"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "at least 20 characters" in str(exc_info.value)

        # Restore valid key
        os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
        get_settings.cache_clear()

    def test_log_level_validation_valid(self, test_env_vars):
        """Test that valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            os.environ["LOG_LEVEL"] = level
            get_settings.cache_clear()
            settings = Settings()
            assert settings.log_level == level.upper()

        # Test case-insensitive
        os.environ["LOG_LEVEL"] = "debug"
        get_settings.cache_clear()
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_log_level_validation_invalid(self, test_env_vars):
        """Test that invalid log level raises ValidationError."""
        os.environ["LOG_LEVEL"] = "INVALID_LEVEL"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "log_level must be one of" in str(exc_info.value)

        # Restore valid level
        os.environ["LOG_LEVEL"] = "INFO"
        get_settings.cache_clear()

    def test_schedule_hour_validation_valid(self, test_env_vars):
        """Test that valid schedule hours are accepted."""
        for hour in [0, 12, 23]:
            os.environ["SCHEDULE_HOUR"] = str(hour)
            get_settings.cache_clear()
            settings = Settings()
            assert settings.schedule_hour == hour

    def test_schedule_hour_validation_invalid(self, test_env_vars):
        """Test that invalid schedule hours raise ValidationError."""
        # Test hour > 23
        os.environ["SCHEDULE_HOUR"] = "24"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "less than or equal to 23" in str(exc_info.value)

        # Test hour < 0
        os.environ["SCHEDULE_HOUR"] = "-1"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "greater than or equal to 0" in str(exc_info.value)

        # Restore valid hour
        os.environ["SCHEDULE_HOUR"] = "2"
        get_settings.cache_clear()

    def test_rag_top_k_validation_valid(self, test_env_vars):
        """Test that valid RAG top_k values are accepted."""
        for k in [1, 5, 20]:
            os.environ["RAG_TOP_K"] = str(k)
            get_settings.cache_clear()
            settings = Settings()
            assert settings.rag_top_k == k

    def test_rag_top_k_validation_invalid(self, test_env_vars):
        """Test that invalid RAG top_k values raise ValidationError."""
        # Test k < 1
        os.environ["RAG_TOP_K"] = "0"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "greater than or equal to 1" in str(exc_info.value)

        # Test k > 20
        os.environ["RAG_TOP_K"] = "21"
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "less than or equal to 20" in str(exc_info.value)

        # Restore valid value
        os.environ["RAG_TOP_K"] = "5"
        get_settings.cache_clear()

    def test_get_cors_origins_list(self, test_env_vars):
        """Test that CORS origins are correctly parsed into a list."""
        settings = get_settings()
        origins = settings.get_cors_origins_list()

        assert isinstance(origins, list)
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_get_cors_origins_list_single_origin(self, test_env_vars):
        """Test CORS origins parsing with single origin."""
        os.environ["CORS_ORIGINS"] = "http://localhost:3000"
        get_settings.cache_clear()

        settings = get_settings()
        origins = settings.get_cors_origins_list()

        assert len(origins) == 1
        assert origins[0] == "http://localhost:3000"

    def test_get_cors_origins_list_with_spaces(self, test_env_vars):
        """Test CORS origins parsing handles spaces correctly."""
        os.environ["CORS_ORIGINS"] = "http://localhost:3000 , http://localhost:5173"
        get_settings.cache_clear()

        settings = get_settings()
        origins = settings.get_cors_origins_list()

        # Should strip spaces
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_settings_cache(self, test_env_vars):
        """Test that get_settings uses caching correctly."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance due to lru_cache
        assert settings1 is settings2

    def test_settings_extra_fields_ignored(self, test_env_vars):
        """Test that extra environment variables are ignored."""
        os.environ["UNKNOWN_FIELD"] = "some_value"
        get_settings.cache_clear()

        # Should not raise an error due to extra='ignore' in model_config
        settings = Settings()
        assert not hasattr(settings, "unknown_field")

        # Cleanup
        os.environ.pop("UNKNOWN_FIELD", None)

    def test_fda_bulk_urls_defaults(self, test_env_vars):
        """Test that FDA bulk URLs have correct default values."""
        settings = get_settings()

        assert settings.fda_bulk_approved_url == "https://download.open.fda.gov/approved_CRLs.zip"
        assert settings.fda_bulk_unapproved_url == "https://download.open.fda.gov/unapproved_CRLs.zip"

    def test_settings_from_env_file(self, tmp_path):
        """Test that settings can be loaded from .env file."""
        # Clear environment variables to test .env file loading
        original_env = {
            "OPENAI_API_KEY": os.environ.pop("OPENAI_API_KEY", None),
            "DATABASE_PATH": os.environ.pop("DATABASE_PATH", None),
            "LOG_LEVEL": os.environ.pop("LOG_LEVEL", None),
        }
        get_settings.cache_clear()

        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=sk-envfile1234567890abcdefghijklmn\n"
            "DATABASE_PATH=/tmp/test.duckdb\n"
            "LOG_LEVEL=ERROR\n"
        )

        # Create settings with custom env_file
        settings = Settings(_env_file=str(env_file))

        assert settings.openai_api_key == "sk-envfile1234567890abcdefghijklmn"
        assert settings.database_path == "/tmp/test.duckdb"
        assert settings.log_level == "ERROR"

        # Restore environment variables
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
        get_settings.cache_clear()
