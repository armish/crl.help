"""
Tests for OpenAI client wrapper.
"""

import pytest
from app.config import Settings
from app.utils.openai_client import OpenAIClient


@pytest.fixture
def dry_run_settings():
    """Settings with dry-run mode enabled."""
    return Settings(
        openai_api_key="sk-dummy-key-for-testing-purposes",
        ai_dry_run=True,
        ai_dry_run_summary_chars=500
    )


@pytest.fixture
def dry_run_client(dry_run_settings):
    """OpenAI client in dry-run mode."""
    return OpenAIClient(dry_run_settings)


class TestOpenAIClientDryRun:
    """Test OpenAI client in dry-run mode."""

    def test_init_dry_run(self, dry_run_client):
        """Test client initialization in dry-run mode."""
        assert dry_run_client.dry_run is True
        assert dry_run_client.client is None

    def test_create_chat_completion_dry_run(self, dry_run_client):
        """Test chat completion in dry-run mode."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "This is a test message with some content."}
        ]

        response = dry_run_client.create_chat_completion(
            model="gpt-5-nano",
            messages=messages
        )

        # Should return a dummy summary
        assert response is not None
        assert isinstance(response, str)
        assert "[DRY-RUN SUMMARY]" in response
        assert len(response) > 0

    def test_create_chat_completion_truncates_long_text(self, dry_run_client):
        """Test that dry-run mode truncates very long text."""
        long_text = "x" * 1000
        messages = [{"role": "user", "content": long_text}]

        response = dry_run_client.create_chat_completion(
            model="gpt-5-nano",
            messages=messages
        )

        # Should be truncated to max_chars + some prefix/suffix
        assert len(response) < len(long_text)
        assert "..." in response

    def test_create_embedding_dry_run(self, dry_run_client):
        """Test embedding generation in dry-run mode."""
        text = "This is a test text for embedding."

        embedding = dry_run_client.create_embedding(text)

        # Should return dummy embedding (default is text-embedding-3-large = 3072 dims)
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 3072  # text-embedding-3-large dimension
        assert all(isinstance(x, float) for x in embedding)
        assert all(x == 0.0 for x in embedding)  # All zeros in dry-run

    def test_generate_dummy_summary_short_text(self, dry_run_client):
        """Test dummy summary generation with short text."""
        text = "Short text"
        summary = dry_run_client._generate_dummy_summary(text)

        assert "[DRY-RUN SUMMARY]" in summary
        assert text in summary

    def test_generate_dummy_summary_long_text(self, dry_run_client):
        """Test dummy summary generation with long text."""
        text = "word " * 200  # Create a long text
        summary = dry_run_client._generate_dummy_summary(text)

        assert "[DRY-RUN SUMMARY]" in summary
        assert "..." in summary
        assert len(summary) <= dry_run_client.settings.ai_dry_run_summary_chars + 50


class TestOpenAIClientConfiguration:
    """Test OpenAI client configuration."""

    def test_custom_summary_chars(self):
        """Test custom summary character limit."""
        settings = Settings(
            openai_api_key="sk-dummy-key-for-testing-purposes",
            ai_dry_run=True,
            ai_dry_run_summary_chars=100
        )
        client = OpenAIClient(settings)

        text = "x" * 500
        messages = [{"role": "user", "content": text}]
        response = client.create_chat_completion("gpt-5-nano", messages)

        # Should respect custom limit
        assert len(response) <= 150  # 100 + prefix + "..."

    def test_dry_run_flag_controls_mode(self):
        """Test that dry_run flag properly controls behavior."""
        # Dry-run enabled
        settings_dry = Settings(
            openai_api_key="sk-dummy-key-for-testing-purposes",
            ai_dry_run=True
        )
        client_dry = OpenAIClient(settings_dry)
        assert client_dry.dry_run is True
        assert client_dry.client is None

        # Dry-run disabled
        settings_real = Settings(
            openai_api_key="sk-test-key-123456789012345678901234",
            ai_dry_run=False
        )
        client_real = OpenAIClient(settings_real)
        assert client_real.dry_run is False
        assert client_real.client is not None


class TestOpenAIClientGPT5Support:
    """Test GPT-5 API support."""

    def test_gpt5_chat_completion_dry_run(self, dry_run_client):
        """Test that GPT-5 models work in dry-run mode."""
        messages = [
            {"role": "user", "content": "Summarize this CRL document."}
        ]

        response = dry_run_client.create_chat_completion(
            model="gpt-5-nano",
            messages=messages
        )

        assert response is not None
        assert isinstance(response, str)
        assert "[DRY-RUN SUMMARY]" in response

    def test_gpt4_chat_completion_dry_run(self, dry_run_client):
        """Test that GPT-4 models still work in dry-run mode."""
        messages = [
            {"role": "user", "content": "Summarize this CRL document."}
        ]

        response = dry_run_client.create_chat_completion(
            model="gpt-4o-mini",
            messages=messages
        )

        assert response is not None
        assert isinstance(response, str)
        assert "[DRY-RUN SUMMARY]" in response


class TestOpenAIClientDynamicDimensions:
    """Test dynamic embedding dimensions for different models."""

    def test_embedding_large_model_3072_dims(self, dry_run_settings):
        """Test that text-embedding-3-large returns 3072 dimensions."""
        settings = Settings(
            openai_api_key="sk-dummy-key-for-testing-purposes",
            ai_dry_run=True,
            openai_embedding_model="text-embedding-3-large"
        )
        client = OpenAIClient(settings)

        embedding = client.create_embedding("test text")

        assert len(embedding) == 3072

    def test_embedding_small_model_1536_dims(self, dry_run_settings):
        """Test that text-embedding-3-small returns 1536 dimensions."""
        settings = Settings(
            openai_api_key="sk-dummy-key-for-testing-purposes",
            ai_dry_run=True,
            openai_embedding_model="text-embedding-3-small"
        )
        client = OpenAIClient(settings)

        embedding = client.create_embedding("test text")

        assert len(embedding) == 1536

    def test_embedding_explicit_model_parameter(self, dry_run_client):
        """Test that explicit model parameter overrides default."""
        # Default is text-embedding-3-large (3072 dims)
        embedding_default = dry_run_client.create_embedding("test text")
        assert len(embedding_default) == 3072

        # Explicitly use small model
        embedding_small = dry_run_client.create_embedding(
            "test text",
            model="text-embedding-3-small"
        )
        assert len(embedding_small) == 1536

        # Explicitly use large model
        embedding_large = dry_run_client.create_embedding(
            "test text",
            model="text-embedding-3-large"
        )
        assert len(embedding_large) == 3072


class TestOpenAIClientErrorHandling:
    """Test error handling in OpenAI client."""

    def test_embedding_with_empty_text(self, dry_run_client):
        """Test that empty text raises appropriate error."""
        # The create_embedding method in the services should handle this,
        # but the client should work with any input in dry-run mode
        embedding = dry_run_client.create_embedding("")
        assert isinstance(embedding, list)
        assert len(embedding) == 3072  # Default is text-embedding-3-large
