"""Unit tests for manager agent — sub-agents and LLM mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.manager import extract_tool_call_summary


@pytest.mark.unit
class TestExtractToolCallSummary:
    def test_extracts_from_both_agents(self, mock_financial_response, mock_competitor_response):
        output = {
            "financial_results": mock_financial_response,
            "competitor_results": mock_competitor_response,
        }
        summary = extract_tool_call_summary(output)
        assert len(summary["financial_tool_calls"]) == 1
        assert len(summary["competitor_tool_calls"]) == 1

    def test_handles_none_results(self):
        summary = extract_tool_call_summary({})
        assert summary["financial_tool_calls"] == []
        assert summary["competitor_tool_calls"] == []


@pytest.mark.unit
class TestRunManagerAgent:
    @pytest.mark.asyncio
    async def test_returns_complete_dict(self, mock_run_financial_agent, mock_run_competitor_agent, mock_llm):
        with patch("src.agents.manager.get_config") as mock_cfg:
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            with patch("src.agents.manager.ChatAnthropic", return_value=mock_llm):
                # Reset singleton so create_manager_agent runs with our mocked LLM
                import src.agents.manager as mgr_mod

                mgr_mod._manager_agent = None

                from src.agents.manager import run_manager_agent

                # The parse_request node calls llm.invoke — mock_llm returns JSON
                # generate_report will call llm.invoke too — mock_llm returns content
                mock_llm.invoke.return_value.content = (
                    '{"companies": ["DataDog", "Dynatrace"], "tickers": ["DDOG", "DT"], "focus": "observability"}'
                )

                result = await run_manager_agent("Compare DataDog to Dynatrace")

                assert "final_report" in result
                assert "companies" in result
                assert "tickers" in result

    @pytest.mark.asyncio
    async def test_handles_top_level_error(self):
        with patch("src.agents.manager.get_manager_agent", side_effect=Exception("fatal")):
            from src.agents.manager import run_manager_agent

            result = await run_manager_agent("test query")
            assert "error" in result
            assert "Error" in result["final_report"] or "fatal" in result["final_report"]

    @pytest.mark.asyncio
    async def test_parse_falls_back_on_json_error(self, mock_run_financial_agent, mock_run_competitor_agent):
        bad_llm = MagicMock()
        bad_llm.invoke.return_value.content = "not valid json"

        with patch("src.agents.manager.get_config") as mock_cfg:
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            with patch("src.agents.manager.ChatAnthropic", return_value=bad_llm):
                import src.agents.manager as mgr_mod

                mgr_mod._manager_agent = None

                from src.agents.manager import run_manager_agent

                result = await run_manager_agent("some query")

                # Should fall back to defaults and still produce a report
                assert "final_report" in result
                assert len(result["companies"]) == 3  # default fallback

    @pytest.mark.asyncio
    async def test_parse_falls_back_on_llm_error(self, mock_run_financial_agent, mock_run_competitor_agent):
        failing_llm = MagicMock()
        # First call (parse) raises, subsequent calls (synthesize) succeed
        failing_llm.invoke.side_effect = [
            Exception("LLM down"),
            MagicMock(content="Fallback report content"),
        ]

        with patch("src.agents.manager.get_config") as mock_cfg:
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            with patch("src.agents.manager.ChatAnthropic", return_value=failing_llm):
                import src.agents.manager as mgr_mod

                mgr_mod._manager_agent = None

                from src.agents.manager import run_manager_agent

                result = await run_manager_agent("some query")

                # Should fall back to defaults
                assert "final_report" in result
                assert len(result["companies"]) == 3

    @pytest.mark.asyncio
    async def test_handles_financial_agent_failure(self, mock_run_competitor_agent, mock_llm):
        """If the financial agent fails, the report is still generated with competitor data."""
        failing_fin = AsyncMock(side_effect=Exception("financial down"))

        with (
            patch("src.agents.manager.run_financial_agent", failing_fin),
            patch("src.agents.manager.get_config") as mock_cfg,
            patch("src.agents.manager.ChatAnthropic", return_value=mock_llm),
        ):
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            import src.agents.manager as mgr_mod

            mgr_mod._manager_agent = None

            from src.agents.manager import run_manager_agent

            result = await run_manager_agent("Compare DataDog to Dynatrace")
            # Should still return a report (partial)
            assert "final_report" in result

    @pytest.mark.asyncio
    async def test_handles_competitor_agent_failure(self, mock_run_financial_agent, mock_llm):
        """If the competitor agent fails, the report is still generated with financial data."""
        failing_comp = AsyncMock(side_effect=Exception("competitor down"))

        with (
            patch("src.agents.manager.run_competitor_agent", failing_comp),
            patch("src.agents.manager.get_config") as mock_cfg,
            patch("src.agents.manager.ChatAnthropic", return_value=mock_llm),
        ):
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            import src.agents.manager as mgr_mod

            mgr_mod._manager_agent = None

            from src.agents.manager import run_manager_agent

            result = await run_manager_agent("Compare DataDog to Dynatrace")
            assert "final_report" in result

    @pytest.mark.asyncio
    async def test_progress_callback_fires(self, mock_run_financial_agent, mock_run_competitor_agent, mock_llm):
        callback = MagicMock()

        with (
            patch("src.agents.manager.get_config") as mock_cfg,
            patch("src.agents.manager.ChatAnthropic", return_value=mock_llm),
        ):
            mock_cfg.return_value.model_name = "test"
            mock_cfg.return_value.model_temperature = 0.0
            mock_cfg.return_value.anthropic_api_key = "test-key"

            import src.agents.manager as mgr_mod

            mgr_mod._manager_agent = None

            from src.agents.manager import run_manager_agent

            await run_manager_agent("Compare DataDog to Dynatrace", progress_callback=callback)

            assert callback.call_count > 0
            stages = {call.args[0]["stage"] for call in callback.call_args_list}
            assert "parse" in stages
            assert "financial" in stages
            assert "synthesize" in stages
