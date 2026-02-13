"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_financial_response():
    """Mock financial agent response."""
    return {
        "task": "Analyze financial metrics",
        "tickers": ["DDOG", "DT", "CSCO"],
        "response": """## Financial Analysis

| Company | Ticker | Market Cap | Revenue (TTM) | Growth |
|---------|--------|------------|---------------|--------|
| DataDog | DDOG | $45B | $2.1B | 25% |
| Dynatrace | DT | $16B | $1.4B | 22% |
| Cisco | CSCO | $220B | $56B | 8% |

All companies show strong performance in the observability market.""",
        "message_count": 5,
    }


@pytest.fixture
def mock_competitor_response():
    """Mock competitor agent response."""
    return {
        "task": "Analyze competitive positioning",
        "companies": ["DataDog", "Dynatrace", "Splunk"],
        "response": """## Competitive Analysis

### DataDog
- **Products**: APM, Infrastructure, Logs, RUM, Security
- **Strengths**: Unified platform, 700+ integrations
- **Weaknesses**: Expensive at scale

### Dynatrace
- **Products**: Full-stack observability, AI-powered
- **Strengths**: Automation, AI capabilities
- **Weaknesses**: Complex deployment

### Splunk (Cisco)
- **Products**: Splunk O11y, AppDynamics
- **Strengths**: Enterprise presence, security focus
- **Weaknesses**: Product overlap post-acquisition""",
        "message_count": 7,
    }


@pytest.fixture
def sample_companies():
    """Sample company list for testing."""
    return ["DataDog", "Dynatrace", "Cisco (Splunk/AppDynamics)"]


@pytest.fixture
def sample_tickers():
    """Sample ticker list for testing."""
    return ["DDOG", "DT", "CSCO"]
