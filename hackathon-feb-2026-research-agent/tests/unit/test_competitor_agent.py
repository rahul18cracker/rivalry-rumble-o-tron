"""Unit tests for competitor agent — LLM and tools mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.competitor import _extract_tool_calls


@pytest.mark.unit
class TestExtractToolCalls:
    def test_extracts_paired_calls(self):
        ai_msg = MagicMock()
        ai_msg.__class__ = type("AIMessage", (), {})
        ai_msg.tool_calls = [
            {"id": "tc1", "name": "search_company_info", "args": {"company_name": "DataDog"}},
        ]

        tool_msg = MagicMock()
        tool_msg.__class__.__name__ = "ToolMessage"
        tool_msg.tool_call_id = "tc1"
        tool_msg.content = "DataDog company info"

        result = _extract_tool_calls([ai_msg, tool_msg])
        assert len(result) == 1
        assert result[0]["tool"] == "search_company_info"

    def test_handles_empty_messages(self):
        assert _extract_tool_calls([]) == []


@pytest.mark.unit
class TestRunCompetitorAgent:
    @pytest.mark.asyncio
    async def test_returns_expected_structure(self):
        mock_agent = MagicMock()
        final_msg = MagicMock()
        final_msg.content = "Competitor analysis result"
        final_msg.tool_calls = []
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "messages": [final_msg],
                "companies": ["DataDog"],
            }
        )

        with patch("src.agents.competitor.get_competitor_agent", return_value=mock_agent):
            from src.agents.competitor import run_competitor_agent

            result = await run_competitor_agent("Analyze competition", ["DataDog"])
            assert result["task"] == "Analyze competition"
            assert result["companies"] == ["DataDog"]
            assert result["response"] == "Competitor analysis result"
            assert isinstance(result["tool_calls"], list)

    @pytest.mark.asyncio
    async def test_returns_error_dict_on_failure(self):
        with patch("src.agents.competitor.get_competitor_agent", side_effect=Exception("boom")):
            from src.agents.competitor import run_competitor_agent

            result = await run_competitor_agent("Analyze competition", ["DataDog"])
            assert "error" in result
            assert result["response"] == ""
            assert result["tool_calls"] == []
