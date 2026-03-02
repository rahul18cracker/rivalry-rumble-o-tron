"""Unit tests for decision tree text visualization (pure logic, no mocks needed)."""

import pytest

from src.report.decision_tree import (
    _friendly_tool_name,
    _short_args,
    build_decision_tree_markdown,
)


@pytest.mark.unit
class TestBuildDecisionTreeMarkdown:
    def test_produces_text_tree(self):
        metadata = {
            "companies": ["DataDog", "Dynatrace"],
            "tickers": ["DDOG", "DT"],
            "financial_tool_calls": [
                {"tool": "get_company_financials", "args": {"ticker": "DDOG"}},
            ],
            "competitor_tool_calls": [
                {"tool": "search_company_info", "args": {"company_name": "DataDog"}},
            ],
        }
        tree = build_decision_tree_markdown(metadata)
        assert "User Query" in tree
        assert "Number Cruncher" in tree
        assert "Street Scout" in tree
        assert "Verdict" in tree
        assert "DDOG" in tree

    def test_handles_empty_tool_calls(self):
        metadata = {
            "companies": ["DataDog"],
            "tickers": ["DDOG"],
            "financial_tool_calls": [],
            "competitor_tool_calls": [],
        }
        tree = build_decision_tree_markdown(metadata)
        assert "0 tool calls" in tree

    def test_handles_empty_metadata(self):
        tree = build_decision_tree_markdown({})
        assert "User Query" in tree
        assert "0 tool calls" in tree


@pytest.mark.unit
class TestShortArgs:
    def test_truncates_long_values(self):
        args = {"query": "x" * 100}
        result = _short_args(args)
        assert "..." in result
        # Total length of value part should be capped at ~50 chars
        value_part = result.split("=", 1)[1]
        assert len(value_part) <= 50

    def test_joins_list_values(self):
        args = {"tickers": ["DDOG", "DT", "CSCO"]}
        result = _short_args(args)
        assert "DDOG" in result
        assert "DT" in result

    def test_empty_args(self):
        assert _short_args({}) == ""


@pytest.mark.unit
class TestFriendlyToolName:
    def test_maps_known_tools(self):
        assert _friendly_tool_name("get_company_financials") == "Company Financials"
        assert _friendly_tool_name("search_company_info") == "Company Info Search"

    def test_falls_back_on_unknown(self):
        result = _friendly_tool_name("some_unknown_tool")
        assert result == "Some Unknown Tool"
