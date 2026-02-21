"""Reusable retry decorator for transient failures."""

import logging

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..logging_config import get_logger

logger = get_logger(__name__)

# Exception types that indicate transient / retryable failures
TRANSIENT_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)


def retry_transient(max_attempts: int = 3):
    """Retry decorator for transient network/API errors.

    Retries on ConnectionError, TimeoutError, and OSError with exponential
    backoff. Does NOT retry on ValueError, KeyError, TypeError, or other
    programming errors.

    Args:
        max_attempts: Maximum number of attempts (default 3).
    """
    return retry(
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
