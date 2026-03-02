"""Market intelligence tools for market sizing, forecasts, news, and sentiment research."""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

# Reuse the lazy Tavily client pattern
_tavily_client = None


def _get_client():
    """Get or create Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


@tool
def search_market_size(market: str) -> dict[str, Any]:
    """
    Search for market size estimates including TAM, SAM, and SOM.

    Args:
        market: Market segment to research (e.g., "observability platform market", "APM market")

    Returns:
        Dictionary with market size estimates including:
        - market: Market segment searched
        - results: List of relevant search results
        - sources: List of source URLs
    """
    try:
        client = _get_client()

        query = f"{market} market size TAM SAM revenue estimate 2024 2025"
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

        results = []
        sources = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            })
            sources.append(item.get("url", ""))

        return {
            "market": market,
            "results": results,
            "sources": sources,
            "source": "tavily",
        }
    except Exception as e:
        return {
            "market": market,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_industry_forecast(market: str) -> dict[str, Any]:
    """
    Search for industry growth forecasts and CAGR projections.

    Args:
        market: Market or industry to research (e.g., "observability market", "cloud monitoring")

    Returns:
        Dictionary with forecast information including:
        - market: Market segment searched
        - results: List of relevant search results
        - sources: List of source URLs
    """
    try:
        client = _get_client()

        query = f"{market} growth forecast CAGR projection 2025 2030"
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

        results = []
        sources = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            })
            sources.append(item.get("url", ""))

        return {
            "market": market,
            "results": results,
            "sources": sources,
            "source": "tavily",
        }
    except Exception as e:
        return {
            "market": market,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_recent_news(company_name: str) -> dict[str, Any]:
    """
    Search for recent news, M&A activity, and partnership announcements for a company.

    Args:
        company_name: Name of the company to research (e.g., "DataDog", "Dynatrace")

    Returns:
        Dictionary with recent news including:
        - company: Company name searched
        - results: List of relevant news items
        - sources: List of source URLs
    """
    try:
        client = _get_client()

        query = f"{company_name} latest news announcements partnerships acquisitions 2025"
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

        results = []
        sources = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            })
            sources.append(item.get("url", ""))

        return {
            "company": company_name,
            "results": results,
            "sources": sources,
            "source": "tavily",
        }
    except Exception as e:
        return {
            "company": company_name,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_analyst_sentiment(company_name: str) -> dict[str, Any]:
    """
    Search for analyst opinions, ratings, and sentiment about a company.

    Args:
        company_name: Name of the company to research (e.g., "DataDog", "Dynatrace")

    Returns:
        Dictionary with analyst sentiment including:
        - company: Company name searched
        - results: List of relevant analyst opinions
        - sources: List of source URLs
    """
    try:
        client = _get_client()

        query = f"{company_name} analyst rating sentiment outlook price target 2025"
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

        results = []
        sources = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            })
            sources.append(item.get("url", ""))

        return {
            "company": company_name,
            "results": results,
            "sources": sources,
            "source": "tavily",
        }
    except Exception as e:
        return {
            "company": company_name,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }
