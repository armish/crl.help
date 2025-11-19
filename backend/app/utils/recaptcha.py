"""
reCAPTCHA v3 validation utility.

Provides functions to verify reCAPTCHA tokens with Google's API
to protect semantic search endpoints from abuse.
"""

import httpx
import logging
from typing import Tuple

from app.config import Settings

logger = logging.getLogger(__name__)


async def verify_recaptcha(
    token: str,
    remote_ip: str,
    settings: Settings
) -> Tuple[bool, float, str]:
    """
    Verify reCAPTCHA v3 token with Google API.

    Args:
        token: reCAPTCHA response token from frontend
        remote_ip: Client's IP address
        settings: Application settings with reCAPTCHA configuration

    Returns:
        Tuple of (is_valid, score, error_message)
        - is_valid: True if token is valid and score >= min_score
        - score: reCAPTCHA score (0.0-1.0, higher is more human-like)
        - error_message: Error description if validation failed, empty string if success

    Example:
        >>> is_valid, score, error = await verify_recaptcha(token, "1.2.3.4", settings)
        >>> if is_valid:
        >>>     # Process request
        >>> else:
        >>>     # Reject request with error message
    """
    # Skip validation if no secret key configured (dev mode)
    if not settings.recaptcha_secret_key:
        logger.warning("reCAPTCHA secret key not configured, skipping validation")
        return True, 1.0, ""

    # Validate inputs
    if not token or not token.strip():
        return False, 0.0, "Missing reCAPTCHA token"

    try:
        # Call Google reCAPTCHA siteverify API
        url = "https://www.google.com/recaptcha/api/siteverify"
        data = {
            "secret": settings.recaptcha_secret_key,
            "response": token,
            "remoteip": remote_ip
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            result = response.json()

        # Check response
        success = result.get("success", False)
        score = result.get("score", 0.0)
        error_codes = result.get("error-codes", [])
        action = result.get("action", "")
        challenge_ts = result.get("challenge_ts", "")

        # Log verification attempt
        logger.info(
            f"reCAPTCHA verification: success={success}, score={score}, "
            f"action={action}, errors={error_codes}"
        )

        # Check for errors
        if not success:
            error_msg = f"reCAPTCHA verification failed: {', '.join(error_codes)}"
            return False, 0.0, error_msg

        # Check score against minimum threshold
        if score < settings.recaptcha_min_score:
            error_msg = (
                f"reCAPTCHA score too low: {score:.2f} < {settings.recaptcha_min_score} "
                "(likely bot activity)"
            )
            return False, score, error_msg

        # Success
        return True, score, ""

    except httpx.TimeoutException:
        logger.error("reCAPTCHA verification timeout")
        return False, 0.0, "reCAPTCHA verification timeout"

    except httpx.HTTPStatusError as e:
        logger.error(f"reCAPTCHA API error: {e}")
        return False, 0.0, f"reCAPTCHA API error: {e.response.status_code}"

    except Exception as e:
        logger.error(f"Unexpected error during reCAPTCHA verification: {e}")
        return False, 0.0, "reCAPTCHA verification failed"


def is_recaptcha_enabled(settings: Settings) -> bool:
    """
    Check if reCAPTCHA validation is enabled.

    Args:
        settings: Application settings

    Returns:
        True if reCAPTCHA secret key is configured, False otherwise
    """
    return bool(settings.recaptcha_secret_key)
