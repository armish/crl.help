"""
OpenAI API client wrapper with dry-run mode support.

This module provides a centralized interface to OpenAI's API with:
- Automatic retry logic for transient failures
- Dry-run mode for development/testing without API costs
- Consistent error handling
- Logging for debugging and monitoring
"""

import logging
from typing import List, Optional
from openai import OpenAI, OpenAIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from app.config import Settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Wrapper around OpenAI API with dry-run mode and retry logic.

    Attributes:
        settings: Application settings containing API key and model configuration
        client: OpenAI client instance (None in dry-run mode)
        dry_run: Whether dry-run mode is enabled
    """

    def __init__(self, settings: Settings):
        """
        Initialize OpenAI client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.dry_run = settings.ai_dry_run

        if self.dry_run:
            logger.info("OpenAI client initialized in DRY-RUN mode (no API calls)")
            self.client = None
        else:
            logger.info("OpenAI client initialized with API key")
            self.client = OpenAI(api_key=settings.openai_api_key)

    @retry(
        retry=retry_if_exception_type((OpenAIError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def create_chat_completion(
        self,
        model: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Create a chat completion using OpenAI API.

        In dry-run mode, returns a dummy response based on the prompt.

        Args:
            model: Model name to use
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated completion text

        Raises:
            OpenAIError: If API call fails after retries
        """
        if self.dry_run:
            # Generate dummy response based on the last message content
            last_message = messages[-1]["content"] if messages else ""
            dummy_response = self._generate_dummy_summary(last_message)
            logger.debug(f"DRY-RUN: Generated dummy completion ({len(dummy_response)} chars)")
            return dummy_response

        try:
            # GPT-5 models use the simplified responses API
            if model.startswith("gpt-5"):
                # Combine all messages into a single input string
                input_text = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

                response = self.client.responses.create(
                    model=model,
                    input=input_text
                )
                content = response.output_text
                logger.debug(f"OpenAI completion (GPT-5): {len(content)} chars, model={model}")
                return content

            # GPT-4 and earlier use the chat completions API
            else:
                completion_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }

                if max_tokens is not None:
                    completion_params["max_tokens"] = max_tokens

                response = self.client.chat.completions.create(**completion_params)
                content = response.choices[0].message.content

                # Log if content is None or empty
                if not content:
                    logger.warning(f"OpenAI returned empty content. Model: {model}, finish_reason: {response.choices[0].finish_reason}")
                    content = ""

                logger.debug(f"OpenAI completion (GPT-4): {len(content)} chars, model={model}")
                return content

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((OpenAIError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def create_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """
        Create an embedding vector for the given text.

        In dry-run mode, returns a dummy vector of zeros.

        Args:
            text: Text to embed
            model: Model name to use (defaults to settings.openai_embedding_model)

        Returns:
            Embedding vector as list of floats

        Raises:
            OpenAIError: If API call fails after retries
        """
        if model is None:
            model = self.settings.openai_embedding_model

        if self.dry_run:
            # Return a dummy embedding vector (1536 dimensions for text-embedding-3-small)
            dummy_embedding = [0.0] * 1536
            logger.debug("DRY-RUN: Generated dummy embedding vector (1536 dims)")
            return dummy_embedding

        try:
            response = self.client.embeddings.create(
                input=text,
                model=model
            )
            embedding = response.data[0].embedding
            logger.debug(f"OpenAI embedding: {len(embedding)} dims, model={model}")
            return embedding

        except OpenAIError as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def _generate_dummy_summary(self, text: str) -> str:
        """
        Generate a dummy summary for dry-run mode.

        Takes the first N characters of the input text as specified in settings.

        Args:
            text: Input text to summarize

        Returns:
            Dummy summary (first N chars of input)
        """
        max_chars = self.settings.ai_dry_run_summary_chars

        # Extract first N chars
        if len(text) <= max_chars:
            dummy = text
        else:
            # Try to break at a word boundary
            dummy = text[:max_chars]
            last_space = dummy.rfind(" ")
            if last_space > max_chars * 0.8:  # If we can find a space in last 20%
                dummy = dummy[:last_space]
            dummy += "..."

        return f"[DRY-RUN SUMMARY] {dummy}"
