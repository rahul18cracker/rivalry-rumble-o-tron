"""Unit tests for manager agent — sub-agents and LLM mocked."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.manager import extract_tool_call_summary


@pytest.mark.unit
class TestExtractToolCallSummary:
    def test_extracts_from_all_agents(
        self, mock_financial_response, mock_competitor_response, mock_market_intel_response
    ):
        output = {
            "financial_results": mock_financial_response,
            "competitor_results": mock_competitor_response,
            "market_intel_results": mock_market_intel_response,
        }
        summary = extract_tool_call_summary(output)
        assert len(summary["financial_tool_calls"]) == 1
        assert len(summary["competitor_tool_calls"]) == 1
        assert len(summary["market_intel_tool_calls"]) == 2

    def test_handles_none_results(self):
        summary = extract_tool_call_summary({})
        assert summary["financial_tool_calls"] == []
        assert summary["competitor_tool_calls"] == []
        assert summary["market_intel_tool_calls"] == []


@pytest.mark.unit
class TestRunManagerAgent:
    @pytest.mark.asyncio
    async def test_returns_complete_dict(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent, mock_llm
    ):
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
    async def test_parse_falls_back_on_json_error(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent
    ):
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
    async def test_parse_falls_back_on_llm_error(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent
    ):
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
    async def test_handles_financial_agent_failure(
        self, mock_run_competitor_agent, mock_run_market_intel_agent, mock_llm
    ):
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
    async def test_handles_competitor_agent_failure(
        self, mock_run_financial_agent, mock_run_market_intel_agent, mock_llm
    ):
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
    async def test_progress_callback_fires(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent, mock_llm
    ):
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
            assert "market_intel" in stages
            assert "synthesize" in stages


@pytest.mark.unit
class TestFollowUpRouting:
    """Tests for the follow-up routing path through the manager graph."""

    @pytest.mark.asyncio
    async def test_no_prior_report_runs_full_pipeline(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent, mock_llm
    ):
        """When prior_report is None, the full pipeline runs (existing behavior)."""
        # mock_llm returns valid JSON for parse, then text for route (but route won't call LLM
        # since prior_report is None)
        mock_llm.invoke.return_value.content = (
            '{"companies": ["DataDog", "Dynatrace"], "tickers": ["DDOG", "DT"], "focus": "observability"}'
        )

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

            result = await run_manager_agent("Compare DataDog to Dynatrace", prior_report=None)

            assert "final_report" in result
            assert result["query_type"] == "new_research"
            # All 3 sub-agents should have been called
            mock_run_financial_agent.assert_called_once()
            mock_run_competitor_agent.assert_called_once()
            mock_run_market_intel_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_followup_with_agents_runs_selected_agents(
        self,
        mock_run_financial_agent,
        mock_run_competitor_agent,
        mock_run_market_intel_agent,
        mock_prior_report,
        mock_prior_results,
    ):
        """Follow-up routed to followup_with_agents only runs the needed agents."""
        mock_llm = MagicMock()
        # First call: route_query classification
        route_response = MagicMock()
        route_response.content = json.dumps(
            {
                "query_type": "followup_with_agents",
                "agents_needed": ["financial"],
                "focused_task": "Get latest revenue data",
                "reasoning": "Financial question",
            }
        )
        # Second call: synthesize_followup
        synth_response = MagicMock()
        synth_response.content = "DataDog has higher revenue growth due to cloud adoption."

        mock_llm.invoke.side_effect = [route_response, synth_response]

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

            result = await run_manager_agent(
                "Why does DataDog have higher revenue growth?",
                prior_report=mock_prior_report,
                prior_results=mock_prior_results,
            )

            assert result["query_type"] == "followup_with_agents"
            assert "financial" in result["followup_agents"]
            # Only financial agent should have been called
            mock_run_financial_agent.assert_called_once()
            # Competitor and market_intel should NOT have been called
            mock_run_competitor_agent.assert_not_called()
            mock_run_market_intel_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_followup_context_only_skips_all_agents(
        self,
        mock_run_financial_agent,
        mock_run_competitor_agent,
        mock_run_market_intel_agent,
        mock_prior_report,
        mock_prior_results,
    ):
        """Context-only follow-up doesn't re-run any agents."""
        mock_llm = MagicMock()
        # First call: route_query classification
        route_response = MagicMock()
        route_response.content = json.dumps(
            {
                "query_type": "followup_context_only",
                "agents_needed": [],
                "focused_task": "Extract pricing info",
                "reasoning": "Already in report",
            }
        )
        # Second call: synthesize_followup
        synth_response = MagicMock()
        synth_response.content = "Based on the report, DataDog uses consumption-based pricing."

        mock_llm.invoke.side_effect = [route_response, synth_response]

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

            result = await run_manager_agent(
                "What did you find about pricing?",
                prior_report=mock_prior_report,
                prior_results=mock_prior_results,
            )

            assert result["query_type"] == "followup_context_only"
            # No agents should have been called
            mock_run_financial_agent.assert_not_called()
            mock_run_competitor_agent.assert_not_called()
            mock_run_market_intel_agent.assert_not_called()
            assert "pricing" in result["final_report"].lower()

    @pytest.mark.asyncio
    async def test_route_error_falls_back_to_full_pipeline(
        self,
        mock_run_financial_agent,
        mock_run_competitor_agent,
        mock_run_market_intel_agent,
        mock_prior_report,
        mock_prior_results,
    ):
        """If route_query classification fails, it falls back to new_research (full pipeline)."""
        mock_llm = MagicMock()
        # First call: route_query gets invalid JSON → falls back to new_research
        route_response = MagicMock()
        route_response.content = "I cannot classify this"
        # Second call: parse_request
        parse_response = MagicMock()
        parse_response.content = '{"companies": ["DataDog", "Dynatrace"], "tickers": ["DDOG", "DT"], "focus": "test"}'
        # Third call: synthesize
        synth_response = MagicMock()
        synth_response.content = "Full report content"

        mock_llm.invoke.side_effect = [route_response, parse_response, synth_response]

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

            result = await run_manager_agent(
                "Tell me more",
                prior_report=mock_prior_report,
                prior_results=mock_prior_results,
            )

            # Should fall back to full pipeline
            assert result["query_type"] == "new_research"
            assert "final_report" in result

    @pytest.mark.asyncio
    async def test_followup_progress_callback_includes_route_stage(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_run_market_intel_agent
    ):
        """Progress callback fires 'route' stage for all queries."""
        callback = MagicMock()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = '{"companies": ["DataDog"], "tickers": ["DDOG"], "focus": "test"}'

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

            stages = {call.args[0]["stage"] for call in callback.call_args_list}
            assert "route" in stages
