"""Yahoo Finance tools for financial data retrieval."""

from typing import Any

import yfinance as yf
from langchain_core.tools import tool

from ..logging_config import get_logger
from ..utils.retry import retry_transient

logger = get_logger(__name__)


def _format_large_number(num: float | None) -> str:
    """Format large numbers with B/M suffix."""
    if num is None:
        return "N/A"

    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    else:
        return f"${num:,.0f}"


def _format_percentage(num: float | None) -> str:
    """Format number as percentage."""
    if num is None:
        return "N/A"
    return f"{num * 100:.1f}%"


@retry_transient()
def _fetch_financials(ticker: str) -> dict[str, Any]:
    """Fetch financial data from yfinance (retried on transient errors)."""
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "company_name": info.get("shortName", ticker),
        "ticker": ticker,
        "market_cap": _format_large_number(info.get("marketCap")),
        "market_cap_raw": info.get("marketCap"),
        "revenue_ttm": _format_large_number(info.get("totalRevenue")),
        "revenue_ttm_raw": info.get("totalRevenue"),
        "revenue_growth_yoy": _format_percentage(info.get("revenueGrowth")),
        "revenue_growth_yoy_raw": info.get("revenueGrowth"),
        "gross_margin": _format_percentage(info.get("grossMargins")),
        "gross_margin_raw": info.get("grossMargins"),
        "operating_margin": _format_percentage(info.get("operatingMargins")),
        "operating_margin_raw": info.get("operatingMargins"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "currency": info.get("currency", "USD"),
        "source": "yfinance",
    }


@retry_transient()
def _fetch_historical(ticker: str, years: int) -> dict[str, Any]:
    """Fetch historical revenue from yfinance (retried on transient errors)."""
    stock = yf.Ticker(ticker)
    info = stock.info
    financials = stock.financials

    historical = []

    if financials is not None and not financials.empty:
        # Get total revenue row if it exists
        revenue_row = None
        for row_name in ["Total Revenue", "Revenue"]:
            if row_name in financials.index:
                revenue_row = financials.loc[row_name]
                break

        if revenue_row is not None:
            # Get the last N years
            for i, (date, value) in enumerate(revenue_row.items()):
                if i >= years:
                    break
                if value is not None and not (isinstance(value, float) and value != value):  # Check for NaN
                    historical.append(
                        {
                            "year": date.year,
                            "revenue": value,
                            "revenue_formatted": _format_large_number(value),
                        }
                    )

    return {
        "company_name": info.get("shortName", ticker),
        "ticker": ticker,
        "historical_revenue": sorted(historical, key=lambda x: x["year"]),
        "source": "yfinance",
    }


@tool
def get_company_financials(ticker: str) -> dict[str, Any]:
    """
    Get key financial metrics for a company.

    Args:
        ticker: Stock ticker symbol (e.g., DDOG, DT, CSCO)

    Returns:
        Dictionary with company financial metrics including:
        - company_name: Full company name
        - ticker: Stock ticker
        - market_cap: Market capitalization
        - revenue_ttm: Trailing twelve months revenue
        - revenue_growth_yoy: Year over year revenue growth
        - gross_margin: Gross profit margin
        - operating_margin: Operating profit margin
        - sector: Company sector
        - industry: Company industry
    """
    if not ticker or not ticker.strip():
        return {"error": "Empty ticker symbol", "ticker": ticker, "source": "yfinance"}

    logger.info("yfinance.get_financials", ticker=ticker)
    try:
        return _fetch_financials(ticker)
    except Exception as e:
        logger.error("yfinance.get_financials.error", ticker=ticker, error=str(e))
        return {
            "error": str(e),
            "ticker": ticker,
            "source": "yfinance",
        }


@tool
def get_historical_revenue(ticker: str, years: int = 3) -> dict[str, Any]:
    """
    Get historical revenue data for a company.

    Args:
        ticker: Stock ticker symbol (e.g., DDOG, DT, CSCO)
        years: Number of years of historical data (default: 3)

    Returns:
        Dictionary with historical revenue data including:
        - company_name: Full company name
        - ticker: Stock ticker
        - historical_revenue: List of yearly revenue data
    """
    if not ticker or not ticker.strip():
        return {"error": "Empty ticker symbol", "ticker": ticker, "historical_revenue": [], "source": "yfinance"}

    logger.info("yfinance.get_historical_revenue", ticker=ticker, years=years)
    try:
        return _fetch_historical(ticker, years)
    except Exception as e:
        logger.error("yfinance.get_historical_revenue.error", ticker=ticker, error=str(e))
        return {
            "error": str(e),
            "ticker": ticker,
            "historical_revenue": [],
            "source": "yfinance",
        }


@tool
def get_company_comparison(tickers: list[str]) -> dict[str, Any]:
    """
    Get comparison metrics for multiple companies.

    Args:
        tickers: List of stock ticker symbols (e.g., ["DDOG", "DT", "CSCO"])

    Returns:
        Dictionary with comparison data for all companies.
    """
    results = {"companies": [], "source": "yfinance"}

    for ticker in tickers:
        data = get_company_financials.invoke({"ticker": ticker})
        results["companies"].append(data)

    return results


# Convenience functions for direct use (non-tool versions)
def fetch_financials(ticker: str) -> dict[str, Any]:
    """Direct function to fetch financials without tool wrapper."""
    return get_company_financials.invoke({"ticker": ticker})


def fetch_historical(ticker: str, years: int = 3) -> dict[str, Any]:
    """Direct function to fetch historical data without tool wrapper."""
    return get_historical_revenue.invoke({"ticker": ticker, "years": years})
