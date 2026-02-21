"""Tavily search tools for competitor research."""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool

from ..logging_config import get_logger
from ..utils.retry import retry_transient

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Lazy import to avoid issues if tavily not installed
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


def _parse_search_results(response: dict) -> tuple[list[dict], list[str]]:
    """Extract results and sources from a Tavily search response."""
    results = []
    sources = []
    for item in response.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            }
        )
        sources.append(item.get("url", ""))
    return results, sources


@retry_transient()
def _search_company(company_name: str) -> dict[str, Any]:
    """Search for company info via Tavily (retried on transient errors)."""
    client = _get_client()
    query = f"{company_name} company overview products services"
    response = client.search(query=query, search_depth="advanced", max_results=5)
    results, sources = _parse_search_results(response)
    return {
        "company": company_name,
        "results": results,
        "sources": sources,
        "source": "tavily",
    }


@retry_transient()
def _search_competitive(company_name: str, competitors: list[str] | None) -> dict[str, Any]:
    """Search for competitive analysis via Tavily (retried on transient errors)."""
    client = _get_client()
    if competitors:
        comp_str = " vs ".join(competitors)
        query = f"{company_name} vs {comp_str} comparison competitive analysis"
    else:
        query = f"{company_name} competitive analysis market position strengths weaknesses"
    response = client.search(query=query, search_depth="advanced", max_results=5)
    results, sources = _parse_search_results(response)
    return {
        "company": company_name,
        "competitors": competitors or [],
        "results": results,
        "sources": sources,
        "source": "tavily",
    }


@retry_transient()
def _search_product(company_name: str, product_category: str) -> dict[str, Any]:
    """Search for product info via Tavily (retried on transient errors)."""
    client = _get_client()
    query = f"{company_name} {product_category} product features pricing"
    response = client.search(query=query, search_depth="advanced", max_results=5)
    results, sources = _parse_search_results(response)
    return {
        "company": company_name,
        "product_category": product_category,
        "results": results,
        "sources": sources,
        "source": "tavily",
    }


@retry_transient()
def _search_trends(topic: str) -> dict[str, Any]:
    """Search for market trends via Tavily (retried on transient errors)."""
    client = _get_client()
    query = f"{topic} market trends analysis forecast"
    response = client.search(query=query, search_depth="advanced", max_results=5)
    results, sources = _parse_search_results(response)
    return {
        "topic": topic,
        "results": results,
        "sources": sources,
        "source": "tavily",
    }


@tool
def search_company_info(company_name: str) -> dict[str, Any]:
    """
    Search for general information about a company.

    Args:
        company_name: Name of the company to research (e.g., "DataDog", "Dynatrace")

    Returns:
        Dictionary with search results including:
        - company: Company name searched
        - results: List of relevant search results
        - sources: List of source URLs
    """
    if not company_name or not company_name.strip():
        return {
            "company": company_name,
            "error": "Empty company name",
            "results": [],
            "sources": [],
            "source": "tavily",
        }

    logger.info("tavily.search_company_info", company=company_name)
    try:
        return _search_company(company_name)
    except Exception as e:
        logger.error("tavily.search_company_info.error", company=company_name, error=str(e))
        return {
            "company": company_name,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_competitive_analysis(company_name: str, competitors: list[str] | None = None) -> dict[str, Any]:
    """
    Search for competitive analysis and market positioning information.

    Args:
        company_name: Name of the company to research
        competitors: Optional list of competitor names to compare against

    Returns:
        Dictionary with competitive analysis results including:
        - company: Company name searched
        - positioning: Market positioning information
        - strengths: List of identified strengths
        - weaknesses: List of identified weaknesses
        - sources: List of source URLs
    """
    logger.info("tavily.search_competitive_analysis", company=company_name, competitors=competitors)
    try:
        return _search_competitive(company_name, competitors)
    except Exception as e:
        logger.error("tavily.search_competitive_analysis.error", company=company_name, error=str(e))
        return {
            "company": company_name,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_product_info(company_name: str, product_category: str) -> dict[str, Any]:
    """
    Search for specific product information.

    Args:
        company_name: Name of the company
        product_category: Product category to search (e.g., "observability", "APM", "monitoring")

    Returns:
        Dictionary with product information.
    """
    logger.info("tavily.search_product_info", company=company_name, category=product_category)
    try:
        return _search_product(company_name, product_category)
    except Exception as e:
        logger.error("tavily.search_product_info.error", company=company_name, error=str(e))
        return {
            "company": company_name,
            "product_category": product_category,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


@tool
def search_market_trends(topic: str) -> dict[str, Any]:
    """
    Search for market trends and industry analysis.

    Args:
        topic: Market or industry topic to research (e.g., "observability market 2024")

    Returns:
        Dictionary with market trend information.
    """
    logger.info("tavily.search_market_trends", topic=topic)
    try:
        return _search_trends(topic)
    except Exception as e:
        logger.error("tavily.search_market_trends.error", topic=topic, error=str(e))
        return {
            "topic": topic,
            "error": str(e),
            "results": [],
            "sources": [],
            "source": "tavily",
        }


# Convenience functions for direct use (non-tool versions)
def fetch_company_info(company_name: str) -> dict[str, Any]:
    """Direct function to fetch company info without tool wrapper."""
    return search_company_info.invoke({"company_name": company_name})


def fetch_competitive_analysis(company_name: str, competitors: list[str] | None = None) -> dict[str, Any]:
    """Direct function to fetch competitive analysis without tool wrapper."""
    return search_competitive_analysis.invoke(
        {
            "company_name": company_name,
            "competitors": competitors,
        }
    )
