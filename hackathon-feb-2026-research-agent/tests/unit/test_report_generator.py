"""Unit tests for report generator — LLM mocked."""

from unittest.mock import MagicMock

import pytest

from src.report.generator import (
    _generate_basic_report,
    format_as_markdown_table,
    generate_report,
)


@pytest.mark.unit
class TestGenerateReport:
    def test_without_llm_produces_basic_report(self):
        report = generate_report(
            query="Test query",
            companies=["DataDog"],
            financial_data={"response": "Financial data here"},
            competitor_data={"response": "Competitor data here"},
            llm=None,
        )
        assert "Test query" in report
        assert "Financial data here" in report
        assert "Competitor data here" in report

    def test_with_mocked_llm_produces_synthesized_report(self, mock_llm):
        mock_llm.invoke.return_value.content = "# Synthesized Report\nGreat content here."

        report = generate_report(
            query="Compare DataDog vs Dynatrace",
            companies=["DataDog", "Dynatrace"],
            financial_data={"response": "fin data"},
            competitor_data={"response": "comp data"},
            llm=mock_llm,
        )
        assert "Synthesized Report" in report

    def test_falls_back_to_basic_on_llm_error(self):
        failing_llm = MagicMock()
        failing_llm.invoke.side_effect = Exception("LLM API error")

        report = generate_report(
            query="Test query",
            companies=["DataDog"],
            financial_data={"response": "fin data"},
            competitor_data={"response": "comp data"},
            llm=failing_llm,
        )
        # Should fall back to basic report, not crash
        assert "Test query" in report
        assert "fin data" in report

    def test_handles_none_data(self):
        report = generate_report(
            query="Test",
            companies=[],
            financial_data=None,
            competitor_data=None,
            llm=None,
        )
        assert report is not None
        assert "not available" in report.lower() or len(report) > 0


@pytest.mark.unit
class TestGenerateBasicReport:
    def test_includes_all_sections(self):
        report = _generate_basic_report(
            query="Analyze observability market",
            companies=["DataDog"],
            financial_response="Revenue: $2.1B",
            competitor_response="Market leader in APM",
        )
        assert "Research Query" in report
        assert "Financial Analysis" in report
        assert "Competitive Analysis" in report
        assert "Revenue: $2.1B" in report
        assert "Market leader in APM" in report

    def test_empty_responses_show_not_available(self):
        report = _generate_basic_report(
            query="Test",
            companies=[],
            financial_response="",
            competitor_response="",
        )
        assert "not available" in report


@pytest.mark.unit
class TestFormatAsMarkdownTable:
    def test_formats_correctly(self):
        table = format_as_markdown_table(
            headers=["Company", "Revenue"],
            rows=[["DataDog", "$2.1B"], ["Dynatrace", "$1.4B"]],
        )
        assert "| Company | Revenue |" in table
        assert "| DataDog | $2.1B |" in table
        assert "| --- | --- |" in table

    def test_handles_empty_input(self):
        assert format_as_markdown_table([], []) == ""
        assert format_as_markdown_table(["A"], []) == ""

    def test_handles_empty_headers(self):
        assert format_as_markdown_table([], [["a"]]) == ""
