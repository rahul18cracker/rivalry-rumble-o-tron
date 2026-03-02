"""Unit tests for the retry decorator."""

import logging
from unittest.mock import MagicMock

import pytest

from src.utils.retry import retry_transient


@pytest.mark.unit
class TestRetryTransient:
    def test_retries_on_connection_error(self):
        """Function that fails twice with ConnectionError then succeeds is retried."""
        func = MagicMock(side_effect=[ConnectionError("conn failed"), ConnectionError("conn failed"), "ok"])
        decorated = retry_transient(max_attempts=3)(func)
        result = decorated()
        assert result == "ok"
        assert func.call_count == 3

    def test_retries_on_timeout_error(self):
        """Function that fails with TimeoutError is retried."""
        func = MagicMock(side_effect=[TimeoutError("timed out"), "ok"])
        decorated = retry_transient(max_attempts=3)(func)
        result = decorated()
        assert result == "ok"
        assert func.call_count == 2

    def test_retries_on_os_error(self):
        """Function that fails with OSError is retried."""
        func = MagicMock(side_effect=[OSError("network unreachable"), "ok"])
        decorated = retry_transient(max_attempts=3)(func)
        result = decorated()
        assert result == "ok"
        assert func.call_count == 2

    def test_gives_up_after_max_attempts(self):
        """Function that always fails exhausts max_attempts and reraises."""
        func = MagicMock(side_effect=ConnectionError("always fails"))
        decorated = retry_transient(max_attempts=3)(func)
        with pytest.raises(ConnectionError, match="always fails"):
            decorated()
        assert func.call_count == 3

    def test_does_not_retry_value_error(self):
        """ValueError is a permanent error — not retried."""
        func = MagicMock(side_effect=ValueError("bad input"))
        decorated = retry_transient(max_attempts=3)(func)
        with pytest.raises(ValueError, match="bad input"):
            decorated()
        assert func.call_count == 1

    def test_does_not_retry_key_error(self):
        """KeyError is a permanent error — not retried."""
        func = MagicMock(side_effect=KeyError("missing"))
        decorated = retry_transient(max_attempts=3)(func)
        with pytest.raises(KeyError):
            decorated()
        assert func.call_count == 1

    def test_logging_on_retry(self, caplog):
        """Retry attempts are logged at WARNING level."""
        func = MagicMock(side_effect=[ConnectionError("fail"), "ok"])
        decorated = retry_transient(max_attempts=3)(func)
        with caplog.at_level(logging.WARNING):
            result = decorated()
        assert result == "ok"
        # before_sleep_log should have emitted a warning
        assert any("Retrying" in record.message for record in caplog.records)
