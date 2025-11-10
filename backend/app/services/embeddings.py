"""
CRL embeddings service using OpenAI API.

This module provides functionality to generate vector embeddings for CRL text,
enabling semantic search and similarity-based retrieval for the RAG system.
"""

import logging
from typing import List, Optional
from app.config import Settings
from app.utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Service for generating embeddings of CRL text using OpenAI.

    Embeddings are dense vector representations that capture semantic meaning,
    enabling similarity search and retrieval for Q&A functionality.

    Attributes:
        settings: Application settings
        openai_client: OpenAI client wrapper
    """

    def __init__(self, settings: Settings):
        """
        Initialize embeddings service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.openai_client = OpenAIClient(settings)

    def generate_embedding(
        self,
        text: str,
        truncate: bool = True
    ) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Text to embed
            truncate: Whether to truncate very long texts (default: True)

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            OpenAIError: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate very long texts to stay within token limits
        # OpenAI embedding models typically have 8191 token limit
        # Rough estimate: 1 token ≈ 4 chars, so ~30000 chars max
        if truncate and len(text) > 30000:
            truncated_text = text[:30000]
            logger.warning(
                f"Text truncated from {len(text)} to 30000 chars for embedding"
            )
        else:
            truncated_text = text

        try:
            embedding = self.openai_client.create_embedding(
                text=truncated_text,
                model=self.settings.openai_embedding_model
            )

            logger.debug(
                f"Generated embedding: {len(embedding)} dims "
                f"(dry_run={self.settings.ai_dry_run})"
            )
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def batch_generate_embeddings(
        self,
        texts: List[tuple[str, str]],
        truncate: bool = True
    ) -> List[tuple[str, Optional[List[float]], Optional[str]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of (id, text) tuples
            truncate: Whether to truncate very long texts

        Returns:
            List of (id, embedding, error) tuples.
            If successful, error is None. If failed, embedding is None.
        """
        results = []

        for item_id, text in texts:
            try:
                embedding = self.generate_embedding(text, truncate=truncate)
                results.append((item_id, embedding, None))
                logger.info(f"Successfully generated embedding for {item_id}")

            except Exception as e:
                error_msg = str(e)
                results.append((item_id, None, error_msg))
                logger.error(f"Failed to generate embedding for {item_id}: {error_msg}")

        successful = sum(1 for _, emb, _ in results if emb is not None)
        logger.info(
            f"Batch embedding generation complete: {successful}/{len(texts)} successful"
        )

        return results

    def generate_query_embedding(
        self,
        query: str
    ) -> List[float]:
        """
        Generate an embedding for a search query.

        This is a convenience method that's identical to generate_embedding()
        but provides a clearer semantic meaning when used for queries.

        Args:
            query: Search query text

        Returns:
            Query embedding vector

        Raises:
            ValueError: If query is empty
            OpenAIError: If API call fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(f"Generating query embedding (dry_run={self.settings.ai_dry_run})")
        return self.generate_embedding(query, truncate=False)

    def generate_combined_embedding(
        self,
        texts: List[str],
        weights: Optional[List[float]] = None
    ) -> List[float]:
        """
        Generate a combined embedding from multiple text segments.

        This is useful when you want to create a single embedding that represents
        multiple pieces of text (e.g., title + summary + key excerpts).

        Args:
            texts: List of text segments to combine
            weights: Optional weights for each segment (must sum to 1.0)
                    If None, equal weights are used.

        Returns:
            Combined embedding vector

        Raises:
            ValueError: If texts is empty or weights are invalid
        """
        if not texts:
            raise ValueError("texts cannot be empty")

        # Generate embeddings for each text
        embeddings = []
        for i, text in enumerate(texts):
            try:
                emb = self.generate_embedding(text)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to embed text segment {i}: {e}")
                continue

        if not embeddings:
            raise ValueError("Failed to generate any embeddings")

        # Use equal weights if not provided
        if weights is None:
            weights = [1.0 / len(embeddings)] * len(embeddings)
        elif len(weights) != len(embeddings):
            raise ValueError(
                f"Number of weights ({len(weights)}) must match "
                f"number of embeddings ({len(embeddings)})"
            )
        elif abs(sum(weights) - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {sum(weights)}")

        # Compute weighted average
        dim = len(embeddings[0])
        combined = [0.0] * dim

        for embedding, weight in zip(embeddings, weights):
            for i in range(dim):
                combined[i] += embedding[i] * weight

        logger.info(f"Generated combined embedding from {len(texts)} text segments")
        return combined
