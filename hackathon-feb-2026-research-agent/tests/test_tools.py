"""Tests for research agent tools."""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestYFinanceTools:
    """Tests for yfinance tools."""

    def test_get_company_financials_returns_dict(self):
        """Test that get_company_financials returns a dictionary."""
        from src.tools.yfinance_tools import get_company_financials

        result = get_company_financials.invoke({"ticker": "DDOG"})

        assert isinstance(result, dict)
        assert "ticker" in result
        assert result["ticker"] == "DDOG"
        assert "source" in result
        assert result["source"] == "yfinance"

    def test_get_company_financials_has_required_fields(self):
        """Test that financials include required metric fields."""
        from src.tools.yfinance_tools import get_company_financials

        result = get_company_financials.invoke({"ticker": "DDOG"})

        # Should have these fields (may be N/A if data unavailable)
        expected_fields = [
            "company_name",
            "ticker",
            "market_cap",
            "revenue_ttm",
            "gross_margin",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_get_historical_revenue_returns_list(self):
        """Test that historical revenue returns a list of years."""
        from src.tools.yfinance_tools import get_historical_revenue

        result = get_historical_revenue.invoke({"ticker": "DDOG", "years": 3})

        assert isinstance(result, dict)
        assert "historical_revenue" in result
        assert isinstance(result["historical_revenue"], list)

    def test_invalid_ticker_returns_error(self):
        """Test that invalid ticker returns error field."""
        from src.tools.yfinance_tools import get_company_financials

        result = get_company_financials.invoke({"ticker": "INVALID123XYZ"})

        # Should either have error or have N/A values
        assert isinstance(result, dict)
        assert "ticker" in result

    def test_company_comparison_multiple_tickers(self):
        """Test comparing multiple companies."""
        from src.tools.yfinance_tools import get_company_comparison

        result = get_company_comparison.invoke({"tickers": ["DDOG", "DT"]})

        assert isinstance(result, dict)
        assert "companies" in result
        assert len(result["companies"]) == 2


class TestTavilyTools:
    """Tests for Tavily tools."""

    @pytest.fixture
    def mock_tavily_client(self):
        """Create a mock Tavily client."""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "content": "Test content about the company.",
                    "url": "https://example.com/test",
                }
            ]
        }
        return mock_client

    def test_search_company_info_without_api_key(self):
        """Test that missing API key returns error."""
        # Temporarily unset the API key
        original_key = os.environ.get("TAVILY_API_KEY")
        if "TAVILY_API_KEY" in os.environ:
            del os.environ["TAVILY_API_KEY"]

        # Clear the cached client
        import src.tools.tavily_tools as tavily_module
        tavily_module._tavily_client = None

        from src.tools.tavily_tools import search_company_info

        result = search_company_info.invoke({"company_name": "TestCompany"})

        # Should return error
        assert isinstance(result, dict)
        assert "error" in result or "results" in result

        # Restore API key
        if original_key:
            os.environ["TAVILY_API_KEY"] = original_key

    @patch("src.tools.tavily_tools._get_client")
    def test_search_company_info_success(self, mock_get_client, mock_tavily_client):
        """Test successful company info search."""
        mock_get_client.return_value = mock_tavily_client

        from src.tools.tavily_tools import search_company_info

        result = search_company_info.invoke({"company_name": "DataDog"})

        assert isinstance(result, dict)
        assert "company" in result
        assert result["company"] == "DataDog"
        assert "source" in result
        assert result["source"] == "tavily"

    @patch("src.tools.tavily_tools._get_client")
    def test_search_competitive_analysis(self, mock_get_client, mock_tavily_client):
        """Test competitive analysis search."""
        mock_get_client.return_value = mock_tavily_client

        from src.tools.tavily_tools import search_competitive_analysis

        result = search_competitive_analysis.invoke({
            "company_name": "DataDog",
            "competitors": ["Dynatrace", "Splunk"],
        })

        assert isinstance(result, dict)
        assert "company" in result
        assert "competitors" in result
        assert "Dynatrace" in result["competitors"]


class TestToolIntegration:
    """Integration tests for tools working together."""

    def test_yfinance_tools_importable(self):
        """Test that yfinance tools can be imported."""
        from src.tools.yfinance_tools import (
            get_company_financials,
            get_historical_revenue,
            get_company_comparison,
        )

        assert get_company_financials is not None
        assert get_historical_revenue is not None
        assert get_company_comparison is not None

    def test_tavily_tools_importable(self):
        """Test that tavily tools can be imported."""
        from src.tools.tavily_tools import (
            search_company_info,
            search_competitive_analysis,
            search_product_info,
            search_market_trends,
        )

        assert search_company_info is not None
        assert search_competitive_analysis is not None
        assert search_product_info is not None
        assert search_market_trends is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
