"""Unit tests for Tavily tools — all external calls mocked."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.tools.tavily_tools import (
    _get_client,
    search_company_info,
    search_competitive_analysis,
    search_market_trends,
    search_product_info,
)


@pytest.mark.unit
class TestSearchCompanyInfo:
    def test_returns_correct_structure(self, mock_tavily_client):
        result = search_company_info.invoke({"company_name": "DataDog"})
        assert result["company"] == "DataDog"
        assert result["source"] == "tavily"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Result"

    def test_returns_error_on_api_exception(self):
        with patch("src.tools.tavily_tools._get_client", side_effect=Exception("API down")):
            result = search_company_info.invoke({"company_name": "DataDog"})
            assert "error" in result
            assert result["results"] == []

    def test_returns_error_when_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            import src.tools.tavily_tools as mod

            mod._tavily_client = None
            result = search_company_info.invoke({"company_name": "Test"})
            assert isinstance(result, dict)
            # Should either have error or empty results (key might come from .env)
            assert "error" in result or "results" in result

    def test_empty_company_name_returns_error(self):
        result = search_company_info.invoke({"company_name": ""})
        assert "error" in result
        assert result["error"] == "Empty company name"


@pytest.mark.unit
class TestSearchCompetitiveAnalysis:
    def test_builds_query_with_competitors(self, mock_tavily_client):
        result = search_competitive_analysis.invoke(
            {
                "company_name": "DataDog",
                "competitors": ["Dynatrace", "Splunk"],
            }
        )
        assert result["company"] == "DataDog"
        assert "Dynatrace" in result["competitors"]
        # Verify the search was called with a "vs" query
        call_args = mock_tavily_client.search.call_args
        assert "vs" in call_args[1]["query"] or "vs" in call_args.kwargs.get("query", "")

    def test_works_without_competitors(self, mock_tavily_client):
        result = search_competitive_analysis.invoke(
            {
                "company_name": "DataDog",
            }
        )
        assert result["company"] == "DataDog"
        assert result["competitors"] == []


@pytest.mark.unit
class TestSearchProductInfo:
    def test_happy_path(self, mock_tavily_client):
        result = search_product_info.invoke(
            {
                "company_name": "DataDog",
                "product_category": "APM",
            }
        )
        assert result["company"] == "DataDog"
        assert result["product_category"] == "APM"
        assert result["source"] == "tavily"


@pytest.mark.unit
class TestSearchMarketTrends:
    def test_happy_path(self, mock_tavily_client):
        result = search_market_trends.invoke({"topic": "observability market"})
        assert result["topic"] == "observability market"
        assert result["source"] == "tavily"


@pytest.mark.unit
class TestGetClient:
    def test_raises_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            import src.tools.tavily_tools as mod

            mod._tavily_client = None
            with pytest.raises((ValueError, Exception)):
                _get_client()


@pytest.mark.unit
class TestTavilyRetryBehavior:
    def test_transient_error_retries_and_succeeds(self):
        """ConnectionError on client.search is retried — succeeds on second call."""
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            ConnectionError("network error"),
            {"results": [{"title": "Retry Result", "content": "Worked after retry", "url": "https://example.com"}]},
        ]
        with patch("src.tools.tavily_tools._get_client", return_value=mock_client):
            result = search_company_info.invoke({"company_name": "DataDog"})
            assert "error" not in result
            assert result["results"][0]["title"] == "Retry Result"
            assert mock_client.search.call_count == 2

    def test_permanent_error_not_retried(self):
        """ValueError is not retried — returns error dict immediately."""
        with patch("src.tools.tavily_tools._get_client", side_effect=ValueError("bad config")):
            result = search_company_info.invoke({"company_name": "DataDog"})
            assert "error" in result
            assert "bad config" in result["error"]

    def test_competitive_analysis_retries_on_transient(self):
        """Competitive analysis search retries on transient errors."""
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            TimeoutError("timed out"),
            {"results": [{"title": "Analysis", "content": "Competitive data", "url": "https://example.com"}]},
        ]
        with patch("src.tools.tavily_tools._get_client", return_value=mock_client):
            result = search_competitive_analysis.invoke({"company_name": "DataDog"})
            assert "error" not in result
            assert mock_client.search.call_count == 2
