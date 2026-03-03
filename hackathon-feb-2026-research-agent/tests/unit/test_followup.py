"""Unit tests for follow-up routing and synthesis logic."""

import json
from unittest.mock import MagicMock

import pytest

from src.agents.followup import build_focused_task, route_query, synthesize_followup

SAMPLE_PRIOR_REPORT = """# Competitive Analysis: DataDog vs Dynatrace

## Financial Summary
DataDog (DDOG) has 25% revenue growth and $2.1B TTM revenue.
Dynatrace (DT) has 20% revenue growth and $1.4B TTM revenue.

## Competitive Positioning
DataDog offers a unified observability platform with 20+ integrations.
Dynatrace focuses on AI-powered full-stack observability.

## Market Intelligence
The observability market is estimated at $20B, growing at 12% CAGR.
"""


def _make_route_response(query_type, agents_needed, focused_task, reasoning):
    """Helper to build a mock LLM response for route_query."""
    return json.dumps(
        {
            "query_type": query_type,
            "agents_needed": agents_needed,
            "focused_task": focused_task,
            "reasoning": reasoning,
        }
    )


@pytest.mark.unit
class TestRouteQuery:
    def test_no_prior_report_returns_new_research(self):
        """Without a prior report, route_query always returns new_research."""
        llm = MagicMock()
        result = route_query("Compare AWS vs Azure", prior_report=None, llm=llm)
        assert result["query_type"] == "new_research"
        assert result["agents_needed"] == []
        # LLM should NOT have been called
        llm.invoke.assert_not_called()

    def test_classifies_followup_with_agents(self):
        """Follow-up needing agent re-runs is classified correctly."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["financial"],
            "Get latest revenue data",
            "Needs fresh financials",
        )
        llm.invoke.return_value = response

        result = route_query(
            "Why does DataDog have higher revenue growth?",
            SAMPLE_PRIOR_REPORT,
            llm,
        )
        assert result["query_type"] == "followup_with_agents"
        assert result["agents_needed"] == ["financial"]
        assert result["focused_task"] == "Get latest revenue data"

    def test_classifies_followup_context_only(self):
        """Context-only follow-ups are classified correctly."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_context_only",
            [],
            "Extract pricing info from report",
            "Already in the report",
        )
        llm.invoke.return_value = response

        result = route_query(
            "What did you find about their pricing?",
            SAMPLE_PRIOR_REPORT,
            llm,
        )
        assert result["query_type"] == "followup_context_only"
        assert result["agents_needed"] == []

    def test_classifies_new_research_with_prior(self):
        """New topic despite having a prior report routes to new_research."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "new_research",
            [],
            "Compare cloud providers",
            "Different companies",
        )
        llm.invoke.return_value = response

        result = route_query("Compare AWS vs Azure vs GCP", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "new_research"

    def test_returns_correct_agents_for_financial_query(self):
        """Financial follow-up returns financial agent."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["financial"],
            "Check margins",
            "Financial data needed",
        )
        llm.invoke.return_value = response

        result = route_query("What are their gross margins?", SAMPLE_PRIOR_REPORT, llm)
        assert "financial" in result["agents_needed"]

    def test_returns_correct_agents_for_competitor_query(self):
        """Competitor follow-up returns competitor agent."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["competitor"],
            "Compare products",
            "Competitive data needed",
        )
        llm.invoke.return_value = response

        result = route_query("How do their APM products compare?", SAMPLE_PRIOR_REPORT, llm)
        assert "competitor" in result["agents_needed"]

    def test_returns_correct_agents_for_market_intel_query(self):
        """Market intel follow-up returns market_intel agent."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["market_intel"],
            "APM trends",
            "Market data needed",
        )
        llm.invoke.return_value = response

        result = route_query("Tell me more about APM market trends", SAMPLE_PRIOR_REPORT, llm)
        assert "market_intel" in result["agents_needed"]

    def test_multiple_agents_needed(self):
        """Follow-up may require multiple agents."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["financial", "competitor"],
            "Deep dive pricing vs revenue",
            "Need both",
        )
        llm.invoke.return_value = response

        result = route_query(
            "Compare pricing strategy vs revenue impact",
            SAMPLE_PRIOR_REPORT,
            llm,
        )
        assert result["query_type"] == "followup_with_agents"
        assert set(result["agents_needed"]) == {"financial", "competitor"}

    def test_graceful_fallback_on_json_error(self):
        """Invalid JSON from LLM falls back to new_research."""
        llm = MagicMock()
        response = MagicMock()
        response.content = "I think this is a follow-up question about financials."
        llm.invoke.return_value = response

        result = route_query("Tell me more about margins", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "new_research"
        assert result["agents_needed"] == []

    def test_graceful_fallback_on_llm_error(self):
        """LLM exception falls back to new_research."""
        llm = MagicMock()
        llm.invoke.side_effect = Exception("API down")

        result = route_query("Tell me more", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "new_research"
        assert result["agents_needed"] == []

    def test_invalid_query_type_falls_back(self):
        """Unknown query_type value falls back to new_research."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "unknown_type",
            [],
            "test",
            "test",
        )
        llm.invoke.return_value = response

        result = route_query("test", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "new_research"

    def test_invalid_agent_names_filtered_out(self):
        """Invalid agent names in agents_needed are filtered out."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["financial", "nonexistent_agent"],
            "test",
            "test",
        )
        llm.invoke.return_value = response

        result = route_query("test", SAMPLE_PRIOR_REPORT, llm)
        assert result["agents_needed"] == ["financial"]

    def test_followup_with_no_valid_agents_falls_back(self):
        """followup_with_agents but all agents invalid falls back to new_research."""
        llm = MagicMock()
        response = MagicMock()
        response.content = _make_route_response(
            "followup_with_agents",
            ["invalid"],
            "test",
            "test",
        )
        llm.invoke.return_value = response

        result = route_query("test", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "new_research"

    def test_handles_markdown_code_fence_in_response(self):
        """JSON wrapped in markdown code fences is still parsed."""
        inner = _make_route_response(
            "followup_context_only",
            [],
            "extract info",
            "in report",
        )
        llm = MagicMock()
        response = MagicMock()
        response.content = f"```json\n{inner}\n```"
        llm.invoke.return_value = response

        result = route_query("What did you find?", SAMPLE_PRIOR_REPORT, llm)
        assert result["query_type"] == "followup_context_only"


@pytest.mark.unit
class TestBuildFocusedTask:
    def test_produces_enriched_task_string(self):
        """Task string includes context from prior report and follow-up question."""
        task = build_focused_task(
            agent_type="financial",
            followup_query="Why does DataDog have higher margins?",
            prior_report=SAMPLE_PRIOR_REPORT,
            companies=["DataDog", "Dynatrace"],
        )
        assert "DataDog" in task
        assert "Dynatrace" in task
        assert "higher margins" in task
        assert "FOLLOW-UP INVESTIGATION" in task

    def test_includes_agent_specific_focus(self):
        """Different agent types get different focused task descriptions."""
        task_fin = build_focused_task("financial", "query", "report", ["A", "B"])
        task_comp = build_focused_task("competitor", "query", "report", ["A", "B"])
        task_market = build_focused_task("market_intel", "query", "report", ["A", "B"])

        assert "financial data" in task_fin.lower()
        assert "competitive positioning" in task_comp.lower()
        assert "market intelligence" in task_market.lower()

    def test_truncates_long_prior_report(self):
        """Very long prior reports are truncated to keep task string manageable."""
        long_report = "x" * 5000
        task = build_focused_task("financial", "query", long_report, ["A"])
        # The template truncates at 2000 chars
        assert len(task) < len(long_report)

    def test_handles_empty_companies(self):
        """Works with empty companies list."""
        task = build_focused_task("financial", "query", "report", [])
        assert "FOLLOW-UP INVESTIGATION" in task


@pytest.mark.unit
class TestSynthesizeFollowup:
    def test_generates_conversational_response(self):
        """Synthesize returns LLM-generated content."""
        llm = MagicMock()
        response = MagicMock()
        response.content = "DataDog has higher margins because of their efficient cloud-native architecture."
        llm.invoke.return_value = response

        result = synthesize_followup(
            query="Why does DataDog have higher margins?",
            prior_report=SAMPLE_PRIOR_REPORT,
            prior_results={"financial_results": {"response": "Margins data..."}},
            new_results=None,
            llm=llm,
        )
        assert "DataDog" in result
        assert "margins" in result.lower()

    def test_includes_new_results_when_provided(self):
        """When new_results are provided, they're passed to the LLM."""
        llm = MagicMock()
        response = MagicMock()
        response.content = "Updated analysis with fresh data."
        llm.invoke.return_value = response

        synthesize_followup(
            query="Latest revenue?",
            prior_report="prior",
            prior_results=None,
            new_results={"financial_results": {"response": "Fresh revenue data"}},
            llm=llm,
        )

        # Verify LLM was called with prompt containing new results
        call_args = llm.invoke.call_args[0][0]
        prompt_content = call_args[0].content  # HumanMessage object
        assert "Fresh revenue data" in prompt_content

    def test_handles_llm_error_gracefully(self):
        """LLM failure returns error message instead of raising."""
        llm = MagicMock()
        llm.invoke.side_effect = Exception("API down")

        result = synthesize_followup(
            query="test",
            prior_report="report",
            prior_results=None,
            new_results=None,
            llm=llm,
        )
        assert "wasn't able to generate" in result

    def test_handles_none_prior_results(self):
        """Works when prior_results is None."""
        llm = MagicMock()
        response = MagicMock()
        response.content = "Here's what I found."
        llm.invoke.return_value = response

        result = synthesize_followup(
            query="test",
            prior_report="report",
            prior_results=None,
            new_results=None,
            llm=llm,
        )
        assert result == "Here's what I found."
