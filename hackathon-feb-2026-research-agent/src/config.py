"""Configuration management for research agent team."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .logging_config import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    anthropic_api_key: str = ""
    tavily_api_key: str = ""

    # Model settings
    model_name: str = "claude-sonnet-4-20250514"
    model_temperature: float = 0.0

    # LangSmith tracing (optional)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "rivalry-rumble-o-tron"

    # Default companies for observability analysis
    default_companies: list = None

    # Ticker mappings
    ticker_map: dict = None

    def __post_init__(self):
        # Load API keys from environment
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")

        # Load LangSmith config from environment
        self.langsmith_tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_api_key = os.getenv("LANGCHAIN_API_KEY", "")
        self.langsmith_project = os.getenv("LANGSMITH_PROJECT", "rivalry-rumble-o-tron")

        # Default companies for demo
        if self.default_companies is None:
            self.default_companies = ["Cisco (Splunk/AppDynamics)", "DataDog", "Dynatrace"]

        # Ticker mappings for financial data
        if self.ticker_map is None:
            self.ticker_map = {
                "cisco": "CSCO",
                "splunk": "CSCO",  # Acquired by Cisco
                "appdynamics": "CSCO",  # Acquired by Cisco
                "datadog": "DDOG",
                "dynatrace": "DT",
            }

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not set")

        if not self.tavily_api_key:
            errors.append("TAVILY_API_KEY not set")

        # Warn (don't error) if tracing is enabled but key is missing
        if self.langsmith_tracing and not self.langsmith_api_key:
            logger.warning("config.langsmith_tracing_enabled_without_key")

        if errors:
            logger.warning("config.validation_errors", errors=errors)
        else:
            logger.info("config.validated")

        return errors

    def configure_tracing(self):
        """Set LangSmith env vars if tracing is enabled and API key is present."""
        if self.langsmith_tracing and self.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
            logger.info("langsmith.tracing.enabled", project=self.langsmith_project)

    def get_ticker(self, company_name: str) -> str | None:
        """Get stock ticker for a company name."""
        name_lower = company_name.lower()

        # Check direct mapping
        for key, ticker in self.ticker_map.items():
            if key in name_lower:
                return ticker

        return None


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
