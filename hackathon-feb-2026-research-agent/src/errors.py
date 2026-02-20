"""Custom exception hierarchy for research agent system."""


class ResearchAgentError(Exception):
    """Base exception for all research agent errors."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class ConfigurationError(ResearchAgentError):
    """Missing or invalid configuration (API keys, settings)."""


class LLMError(ResearchAgentError):
    """LLM call failures (timeout, API error, malformed response)."""


class ToolExecutionError(ResearchAgentError):
    """Tool-level failures (yfinance, Tavily)."""


class OrchestrationError(ResearchAgentError):
    """Agent graph execution failures."""


class ReportGenerationError(ResearchAgentError):
    """Report synthesis failures."""
