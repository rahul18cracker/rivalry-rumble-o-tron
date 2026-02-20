"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Autouse: reset agent/client singletons between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level singletons so tests don't leak state."""
    import src.agents.competitor as comp_mod
    import src.agents.financial as fin_mod
    import src.agents.manager as mgr_mod
    import src.tools.tavily_tools as tavily_mod

    fin_mod._financial_agent = None
    comp_mod._competitor_agent = None
    mgr_mod._manager_agent = None
    tavily_mod._tavily_client = None
    yield


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_companies():
    """Sample company list for testing."""
    return ["DataDog", "Dynatrace", "Cisco (Splunk/AppDynamics)"]


@pytest.fixture
def sample_tickers():
    """Sample ticker list for testing."""
    return ["DDOG", "DT", "CSCO"]


@pytest.fixture
def mock_financial_response():
    """Mock financial agent response dict."""
    return {
        "task": "Analyze financial metrics",
        "tickers": ["DDOG", "DT", "CSCO"],
        "response": (
            "## Financial Analysis\n\n"
            "| Company | Ticker | Market Cap |\n"
            "|---------|--------|------------|\n"
            "| DataDog | DDOG | $45B |\n"
        ),
        "message_count": 5,
        "tool_calls": [
            {
                "tool": "get_company_financials",
                "args": {"ticker": "DDOG"},
                "result_preview": "DataDog financials...",
            }
        ],
    }


@pytest.fixture
def mock_competitor_response():
    """Mock competitor agent response dict."""
    return {
        "task": "Analyze competitive positioning",
        "companies": ["DataDog", "Dynatrace", "Splunk"],
        "response": ("## Competitive Analysis\n\n### DataDog\n- Strengths: Unified platform\n"),
        "message_count": 7,
        "tool_calls": [
            {
                "tool": "search_company_info",
                "args": {"company_name": "DataDog"},
                "result_preview": "DataDog info...",
            }
        ],
    }


# ---------------------------------------------------------------------------
# LLM mock fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_llm():
    """Return a MagicMock that behaves like ChatAnthropic.invoke()."""
    llm = MagicMock()
    response = MagicMock()
    response.content = '{"companies": ["DataDog", "Dynatrace"], "tickers": ["DDOG", "DT"], "focus": "observability"}'
    response.tool_calls = []
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_llm_with_tool_calls():
    """Return a mock LLM whose response includes tool_calls."""
    llm = MagicMock()
    response = MagicMock()
    response.content = ""
    response.tool_calls = [
        {"id": "tc1", "name": "get_company_financials", "args": {"ticker": "DDOG"}},
    ]
    llm.invoke.return_value = response
    return llm


# ---------------------------------------------------------------------------
# Tool mock fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_yfinance_ticker():
    """Patch yf.Ticker to return a mock with .info and .financials."""
    import pandas as pd

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
    mock_ticker.financials = pd.DataFrame(
        {"2024-12-31": [2_100_000_000], "2023-12-31": [1_700_000_000]},
        index=["Total Revenue"],
    )
    mock_ticker.financials.columns = pd.to_datetime(mock_ticker.financials.columns)

    with patch("src.tools.yfinance_tools.yf.Ticker", return_value=mock_ticker) as mock_cls:
        mock_cls._instance = mock_ticker
        yield mock_cls


@pytest.fixture
def mock_tavily_client():
    """Patch _get_client to return a mock TavilyClient."""
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

    with patch("src.tools.tavily_tools._get_client", return_value=mock_client) as mock_get:
        mock_get._client = mock_client
        yield mock_client


# ---------------------------------------------------------------------------
# Agent mock fixtures (for manager tests)
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_run_financial_agent(mock_financial_response):
    """Patch run_financial_agent to return sample data."""
    with patch(
        "src.agents.manager.run_financial_agent",
        new_callable=AsyncMock,
        return_value=mock_financial_response,
    ) as mock_fn:
        yield mock_fn


@pytest.fixture
def mock_run_competitor_agent(mock_competitor_response):
    """Patch run_competitor_agent to return sample data."""
    with patch(
        "src.agents.manager.run_competitor_agent",
        new_callable=AsyncMock,
        return_value=mock_competitor_response,
    ) as mock_fn:
        yield mock_fn
