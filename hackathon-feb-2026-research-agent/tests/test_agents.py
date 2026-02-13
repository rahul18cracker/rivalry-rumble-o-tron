"""Tests for research agents."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestConfig:
    """Tests for configuration."""

    def test_config_loads(self):
        """Test that config loads without error."""
        from src.config import get_config

        config = get_config()
        assert config is not None

    def test_config_has_defaults(self):
        """Test that config has default values."""
        from src.config import get_config

        config = get_config()

        assert config.model_name is not None
        assert config.default_companies is not None
        assert len(config.default_companies) > 0

    def test_config_ticker_mapping(self):
        """Test ticker mapping functionality."""
        from src.config import get_config

        config = get_config()

        assert config.get_ticker("DataDog") == "DDOG"
        assert config.get_ticker("Dynatrace") == "DT"
        assert config.get_ticker("Cisco") == "CSCO"
        assert config.get_ticker("Splunk") == "CSCO"


class TestPrompts:
    """Tests for agent prompts."""

    def test_manager_prompt_exists(self):
        """Test that manager prompt is defined."""
        from src.prompts.manager_prompt import MANAGER_SYSTEM_PROMPT

        assert MANAGER_SYSTEM_PROMPT is not None
        assert len(MANAGER_SYSTEM_PROMPT) > 100
        assert "Manager" in MANAGER_SYSTEM_PROMPT

    def test_financial_prompt_exists(self):
        """Test that financial prompt is defined."""
        from src.prompts.financial_prompt import FINANCIAL_SYSTEM_PROMPT

        assert FINANCIAL_SYSTEM_PROMPT is not None
        assert "Financial" in FINANCIAL_SYSTEM_PROMPT

    def test_competitor_prompt_exists(self):
        """Test that competitor prompt is defined."""
        from src.prompts.competitor_prompt import COMPETITOR_SYSTEM_PROMPT

        assert COMPETITOR_SYSTEM_PROMPT is not None
        assert "Competitor" in COMPETITOR_SYSTEM_PROMPT


class TestFinancialAgent:
    """Tests for financial agent."""

    def test_financial_agent_importable(self):
        """Test that financial agent can be imported."""
        from src.agents.financial import run_financial_agent

        assert run_financial_agent is not None

    @pytest.mark.skipif(
        not pytest.importorskip("langchain_anthropic", reason="Anthropic not installed"),
        reason="Requires langchain-anthropic",
    )
    def test_financial_agent_creates(self):
        """Test that financial agent can be created."""
        from src.agents.financial import create_financial_agent

        # This will fail if API key not set, but we can at least test imports
        try:
            agent = create_financial_agent()
            assert agent is not None
        except Exception as e:
            # Expected if API key not configured
            assert "API" in str(e) or "key" in str(e).lower()


class TestCompetitorAgent:
    """Tests for competitor agent."""

    def test_competitor_agent_importable(self):
        """Test that competitor agent can be imported."""
        from src.agents.competitor import run_competitor_agent

        assert run_competitor_agent is not None


class TestManagerAgent:
    """Tests for manager agent."""

    def test_manager_agent_importable(self):
        """Test that manager agent can be imported."""
        from src.agents.manager import run_manager_agent

        assert run_manager_agent is not None


class TestReportGenerator:
    """Tests for report generator."""

    def test_report_template_exists(self):
        """Test that report template is defined."""
        from src.report.templates import REPORT_TEMPLATE

        assert REPORT_TEMPLATE is not None
        assert "{title}" in REPORT_TEMPLATE
        assert "{executive_summary}" in REPORT_TEMPLATE

    def test_format_companies_table(self):
        """Test company table formatting."""
        from src.report.templates import format_companies_table

        companies = ["DataDog", "Dynatrace"]
        table = format_companies_table(companies)

        assert "DataDog" in table
        assert "DDOG" in table
        assert "|" in table  # Markdown table format

    def test_generate_report_basic(self):
        """Test basic report generation without LLM."""
        from src.report.generator import generate_report

        report = generate_report(
            query="Test query",
            companies=["DataDog"],
            financial_data={"response": "Test financial data"},
            competitor_data={"response": "Test competitor data"},
            llm=None,  # No LLM, use basic generation
        )

        assert report is not None
        assert "Test query" in report
        assert "Financial" in report


class TestAgentIntegration:
    """Integration tests for agents working together."""

    def test_all_agents_importable(self):
        """Test that all agents can be imported from package."""
        from src.agents import (
            run_manager_agent,
            run_financial_agent,
            run_competitor_agent,
        )

        assert run_manager_agent is not None
        assert run_financial_agent is not None
        assert run_competitor_agent is not None

    def test_tools_importable(self):
        """Test that all tools can be imported from package."""
        from src.tools import (
            get_company_financials,
            get_historical_revenue,
            search_company_info,
            search_competitive_analysis,
        )

        assert get_company_financials is not None
        assert get_historical_revenue is not None
        assert search_company_info is not None
        assert search_competitive_analysis is not None


class TestEndToEnd:
    """End-to-end tests (require API keys)."""

    @pytest.mark.skip(reason="Requires API keys - run manually")
    def test_full_research_flow(self):
        """Test complete research flow."""
        from src.agents.manager import run_manager_agent

        report = asyncio.run(run_manager_agent(
            "Compare DataDog to Dynatrace"
        ))

        assert report is not None
        assert len(report) > 100
        assert "DataDog" in report or "DDOG" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
