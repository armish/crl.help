"""
CRL summarization service using OpenAI API.

This module provides functionality to generate concise summaries of Complete Response Letters
using OpenAI's language models. Summaries help users quickly understand the key issues
without reading the entire letter.
"""

import logging
from typing import Optional
from app.config import Settings
from app.utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for generating summaries of CRL text using OpenAI.

    Attributes:
        settings: Application settings
        openai_client: OpenAI client wrapper
    """

    def __init__(self, settings: Settings):
        """
        Initialize summarization service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.openai_client = OpenAIClient(settings)

    def summarize_crl(
        self,
        crl_text: str,
        max_summary_length: int = 300
    ) -> str:
        """
        Generate a concise summary of a CRL.

        Args:
            crl_text: Full text of the Complete Response Letter
            max_summary_length: Maximum length of summary in words

        Returns:
            Generated summary text

        Raises:
            ValueError: If crl_text is empty
            OpenAIError: If API call fails
        """
        if not crl_text or not crl_text.strip():
            raise ValueError("CRL text cannot be empty")

        # Create the prompt with full text
        # Modern models (GPT-5, GPT-4o) support 128K-400K token contexts,
        # so we don't need to truncate CRLs (typically 5K-50K chars / 1K-15K tokens)
        prompt = self._create_summary_prompt(crl_text, max_summary_length)

        # Generate summary
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert in pharmaceutical regulatory affairs, "
                    "specializing in analyzing FDA Complete Response Letters. "
                    "Your summaries are clear, concise, and highlight key deficiencies."
                    "You one-paragraph summary will be read by an executive who wants "
                    "to extract learnings and cautions for future submissions. "
                    "Answer in markdown format. No headers."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            summary = self.openai_client.create_chat_completion(
                model=self.settings.openai_summary_model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=max_summary_length * 2  # Rough estimate: 1 word ≈ 1.5 tokens
            )

            logger.debug(
                f"Generated summary: {len(summary)} chars "
                f"(dry_run={self.settings.ai_dry_run})"
            )
            return summary.strip()

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise

    def _create_summary_prompt(
        self,
        crl_text: str,
        max_length: int
    ) -> str:
        """
        Create the prompt for summary generation.

        Args:
            crl_text: CRL text to summarize
            max_length: Maximum summary length in words

        Returns:
            Formatted prompt
        """
        prompt = f"""Summarize the following FDA Complete Response Letter (CRL) in approximately {max_length} words or less.

Focus on:
1. The main deficiencies or issues identified by the FDA
2. Which areas were problematic (e.g., clinical data, manufacturing, labeling)
3. Any specific actions required from the applicant

CRL Text:
{crl_text}

Provide a clear, concise summary that captures the essential points:"""

        return prompt

    def batch_summarize(
        self,
        crl_texts: list[tuple[str, str]],
        max_summary_length: int = 300
    ) -> list[tuple[str, Optional[str], Optional[str]]]:
        """
        Generate summaries for multiple CRLs.

        Args:
            crl_texts: List of (crl_id, crl_text) tuples
            max_summary_length: Maximum length of each summary in words

        Returns:
            List of (crl_id, summary, error) tuples.
            If successful, error is None. If failed, summary is None.
        """
        results = []

        for crl_id, crl_text in crl_texts:
            try:
                summary = self.summarize_crl(crl_text, max_summary_length)
                results.append((crl_id, summary, None))
                logger.info(f"Successfully summarized CRL {crl_id}")

            except Exception as e:
                error_msg = str(e)
                results.append((crl_id, None, error_msg))
                logger.error(f"Failed to summarize CRL {crl_id}: {error_msg}")

        successful = sum(1 for _, summary, _ in results if summary is not None)
        logger.info(
            f"Batch summarization complete: {successful}/{len(crl_texts)} successful"
        )

        return results
