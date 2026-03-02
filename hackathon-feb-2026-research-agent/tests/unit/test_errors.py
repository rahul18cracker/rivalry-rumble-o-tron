"""Unit tests for custom exception hierarchy."""

import pytest

from src.errors import (
    ConfigurationError,
    LLMError,
    OrchestrationError,
    ReportGenerationError,
    ResearchAgentError,
    ToolExecutionError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    def test_base_exception_exists(self):
        err = ResearchAgentError("test")
        assert str(err) == "test"
        assert err.cause is None

    def test_base_exception_with_cause(self):
        cause = ValueError("root cause")
        err = ResearchAgentError("wrapped", cause=cause)
        assert err.cause is cause

    def test_configuration_error_inherits(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, ResearchAgentError)

    def test_llm_error_inherits(self):
        err = LLMError("llm failed")
        assert isinstance(err, ResearchAgentError)

    def test_tool_execution_error_inherits(self):
        err = ToolExecutionError("tool broke")
        assert isinstance(err, ResearchAgentError)

    def test_orchestration_error_inherits(self):
        err = OrchestrationError("graph failed")
        assert isinstance(err, ResearchAgentError)

    def test_report_generation_error_inherits(self):
        err = ReportGenerationError("report failed")
        assert isinstance(err, ResearchAgentError)

    def test_all_catchable_as_base(self):
        for cls in (ConfigurationError, LLMError, ToolExecutionError, OrchestrationError, ReportGenerationError):
            with pytest.raises(ResearchAgentError):
                raise cls("test")
