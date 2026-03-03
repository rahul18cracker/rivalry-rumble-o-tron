"""Unit tests for financial agent — LLM and tools mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.financial import _extract_structured_data, _extract_tool_calls


@pytest.mark.unit
class TestExtractToolCalls:
    def test_extracts_paired_calls(self):
        ai_msg = MagicMock()
        ai_msg.__class__ = type("AIMessage", (), {})
        ai_msg.tool_calls = [
            {"id": "tc1", "name": "get_company_financials", "args": {"ticker": "DDOG"}},
        ]

        tool_msg = MagicMock()
        tool_msg.__class__.__name__ = "ToolMessage"
        tool_msg.tool_call_id = "tc1"
        tool_msg.content = "Datadog financials data here"

        result = _extract_tool_calls([ai_msg, tool_msg])
        assert len(result) == 1
        assert result[0]["tool"] == "get_company_financials"
        assert result[0]["args"] == {"ticker": "DDOG"}

    def test_handles_empty_messages(self):
        assert _extract_tool_calls([]) == []

    def test_truncates_long_results(self):
        ai_msg = MagicMock()
        ai_msg.tool_calls = [{"id": "tc1", "name": "search", "args": {}}]

        tool_msg = MagicMock()
        tool_msg.__class__.__name__ = "ToolMessage"
        tool_msg.tool_call_id = "tc1"
        tool_msg.content = "x" * 300

        result = _extract_tool_calls([ai_msg, tool_msg])
        assert result[0]["result_preview"].endswith("...")
        assert len(result[0]["result_preview"]) == 203  # 200 + "..."

    def test_handles_messages_without_tool_calls(self):
        msg = MagicMock(spec=[])  # No tool_calls attribute
        result = _extract_tool_calls([msg])
        assert result == []


@pytest.mark.unit
class TestExtractStructuredData:
    def test_extracts_comparison_from_get_company_comparison(self):
        import json

        ai_msg = MagicMock()
        ai_msg.tool_calls = [
            {"id": "tc1", "name": "get_company_comparison", "args": {"tickers": ["DDOG", "DT"]}},
        ]
        tool_result = {
            "companies": [
                {"company_name": "Datadog", "ticker": "DDOG", "revenue_ttm_raw": 2.1e9, "revenue_growth_yoy_raw": 0.29},
                {"company_name": "Dynatrace", "ticker": "DT", "revenue_ttm_raw": 1.4e9, "revenue_growth_yoy_raw": 0.18},
            ],
            "source": "yfinance",
        }
        tool_msg = MagicMock()
        tool_msg.__class__.__name__ = "ToolMessage"
        tool_msg.tool_call_id = "tc1"
        tool_msg.content = json.dumps(tool_result)

        result = _extract_structured_data([ai_msg, tool_msg])
        assert result["comparison"] is not None
        assert len(result["comparison"]["companies"]) == 2
        assert result["comparison"]["companies"][0]["ticker"] == "DDOG"
        assert result["comparison"]["companies"][1]["revenue_ttm_raw"] == 1.4e9

    def test_returns_empty_when_no_tool_messages(self):
        result = _extract_structured_data([])
        assert result["comparison"] is None
        assert result["historical"] == {}


@pytest.mark.unit
class TestRunFinancialAgent:
    @pytest.mark.asyncio
    async def test_returns_expected_structure(self):
        mock_agent = MagicMock()
        final_msg = MagicMock()
        final_msg.content = "Financial analysis result"
        final_msg.tool_calls = []
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "messages": [final_msg],
                "tickers": ["DDOG"],
            }
        )

        with patch("src.agents.financial.get_financial_agent", return_value=mock_agent):
            from src.agents.financial import run_financial_agent

            result = await run_financial_agent("Analyze DDOG", ["DDOG"])
            assert result["task"] == "Analyze DDOG"
            assert result["tickers"] == ["DDOG"]
            assert result["response"] == "Financial analysis result"
            assert isinstance(result["tool_calls"], list)
            assert "structured_data" in result
            assert result["structured_data"]["comparison"] is None

    @pytest.mark.asyncio
    async def test_returns_error_dict_on_failure(self):
        with patch("src.agents.financial.get_financial_agent", side_effect=Exception("boom")):
            from src.agents.financial import run_financial_agent

            result = await run_financial_agent("Analyze DDOG", ["DDOG"])
            assert "error" in result
            assert result["response"] == ""
            assert result["tool_calls"] == []
            assert result["structured_data"] == {"comparison": None, "historical": {}}
