"""Unit tests for yfinance tools — all external calls mocked."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.tools.yfinance_tools import (
    _format_large_number,
    _format_percentage,
    get_company_comparison,
    get_company_financials,
    get_historical_revenue,
)


@pytest.mark.unit
class TestFormatHelpers:
    def test_format_large_number_billions(self):
        assert _format_large_number(45_000_000_000) == "$45.00B"

    def test_format_large_number_millions(self):
        assert _format_large_number(120_000_000) == "$120.00M"

    def test_format_large_number_small(self):
        assert _format_large_number(5000) == "$5,000"

    def test_format_large_number_none(self):
        assert _format_large_number(None) == "N/A"

    def test_format_percentage(self):
        assert _format_percentage(0.25) == "25.0%"

    def test_format_percentage_none(self):
        assert _format_percentage(None) == "N/A"


@pytest.mark.unit
class TestGetCompanyFinancials:
    def test_returns_correct_structure(self, mock_yfinance_ticker):
        result = get_company_financials.invoke({"ticker": "DDOG"})
        assert result["ticker"] == "DDOG"
        assert result["source"] == "yfinance"
        assert result["company_name"] == "Datadog Inc."
        assert result["market_cap"] == "$45.00B"

    def test_returns_error_on_exception(self):
        with patch("src.tools.yfinance_tools.yf.Ticker", side_effect=Exception("network error")):
            result = get_company_financials.invoke({"ticker": "DDOG"})
            assert "error" in result
            assert result["ticker"] == "DDOG"

    def test_empty_ticker_returns_error(self):
        result = get_company_financials.invoke({"ticker": ""})
        assert "error" in result
        assert result["error"] == "Empty ticker symbol"

    def test_whitespace_ticker_returns_error(self):
        result = get_company_financials.invoke({"ticker": "   "})
        assert "error" in result


@pytest.mark.unit
class TestGetHistoricalRevenue:
    def test_returns_historical_list(self, mock_yfinance_ticker):
        result = get_historical_revenue.invoke({"ticker": "DDOG", "years": 3})
        assert isinstance(result["historical_revenue"], list)
        assert result["source"] == "yfinance"

    def test_handles_empty_financials(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"shortName": "Test"}
        mock_ticker.financials = pd.DataFrame()

        with patch("src.tools.yfinance_tools.yf.Ticker", return_value=mock_ticker):
            result = get_historical_revenue.invoke({"ticker": "TEST"})
            assert result["historical_revenue"] == []

    def test_empty_ticker_returns_error(self):
        result = get_historical_revenue.invoke({"ticker": "", "years": 3})
        assert "error" in result


@pytest.mark.unit
class TestGetCompanyComparison:
    def test_calls_financials_for_each_ticker(self, mock_yfinance_ticker):
        result = get_company_comparison.invoke({"tickers": ["DDOG", "DT"]})
        assert "companies" in result
        assert len(result["companies"]) == 2


@pytest.mark.unit
class TestYfinanceRetryBehavior:
    def test_transient_error_retries_and_succeeds(self):
        """ConnectionError is retried — function succeeds on second call."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Datadog Inc.",
            "marketCap": 45_000_000_000,
            "totalRevenue": 2_100_000_000,
            "revenueGrowth": 0.25,
            "grossMargins": 0.78,
            "operatingMargins": 0.05,
            "sector": "Technology",
            "industry": "Software—Application",
            "currency": "USD",
        }
        with patch(
            "src.tools.yfinance_tools.yf.Ticker",
            side_effect=[ConnectionError("network error"), mock_ticker],
        ):
            result = get_company_financials.invoke({"ticker": "DDOG"})
            assert "error" not in result
            assert result["company_name"] == "Datadog Inc."

    def test_permanent_error_not_retried(self):
        """ValueError is not retried — immediately returns error dict."""
        with patch(
            "src.tools.yfinance_tools.yf.Ticker",
            side_effect=ValueError("bad ticker format"),
        ):
            result = get_company_financials.invoke({"ticker": "DDOG"})
            assert "error" in result
            assert "bad ticker format" in result["error"]

    def test_historical_transient_error_retries(self):
        """ConnectionError in historical fetch is retried."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"shortName": "Test"}
        mock_ticker.financials = pd.DataFrame()
        with patch(
            "src.tools.yfinance_tools.yf.Ticker",
            side_effect=[ConnectionError("timeout"), mock_ticker],
        ):
            result = get_historical_revenue.invoke({"ticker": "TEST"})
            assert "error" not in result
            assert result["historical_revenue"] == []
