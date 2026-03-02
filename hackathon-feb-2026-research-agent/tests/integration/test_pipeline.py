"""Integration tests — full pipeline with all externals mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.integration
class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_run_financial_agent, mock_run_competitor_agent, mock_llm):
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

            result = await run_manager_agent("Compare DataDog to Dynatrace")

            assert "final_report" in result
            assert len(result["companies"]) > 0
            assert result["financial_results"] is not None
            assert result["competitor_results"] is not None

    @pytest.mark.asyncio
    async def test_partial_failure_financial_down(self, mock_run_competitor_agent, mock_llm):
        failing_fin = AsyncMock(side_effect=Exception("financial agent down"))

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

            assert "final_report" in result
            # Financial results should be an error dict
            fin = result.get("financial_results", {})
            assert isinstance(fin, dict)

    @pytest.mark.asyncio
    async def test_partial_failure_competitor_down(self, mock_run_financial_agent, mock_llm):
        failing_comp = AsyncMock(side_effect=Exception("competitor agent down"))

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
    async def test_both_agents_fail(self, mock_llm):
        failing_fin = AsyncMock(side_effect=Exception("fin down"))
        failing_comp = AsyncMock(side_effect=Exception("comp down"))

        with (
            patch("src.agents.manager.run_financial_agent", failing_fin),
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

            # Should not crash — still produces some report
            assert "final_report" in result

    @pytest.mark.asyncio
    async def test_progress_callback_receives_expected_stages(
        self, mock_run_financial_agent, mock_run_competitor_agent, mock_llm
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

            # Verify callback was called with structured dicts
            assert callback.call_count >= 4  # at least parse(running,done), financial, competitor, synthesize
            all_dicts = [call.args[0] for call in callback.call_args_list]
            for d in all_dicts:
                assert "stage" in d
                assert "status" in d
