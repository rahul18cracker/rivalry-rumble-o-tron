# Research Agent Team

A multi-agent research system using orchestrator pattern for business and competitor analysis.

## Demo Goal

Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace.

## Architecture

```
                              USER INPUT
                                  │
                                  ▼
                           ┌─────────────┐
                           │    ROUTE    │  ← classifies query type
                           └──────┬──────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
       new_research      followup_with_agents  followup_context_only
              │                   │                   │
              ▼                   ▼                   │
         ┌────────┐     ┌────────────────┐           │
         │ PARSE  │     │ EXECUTE SUBSET │           │
         └───┬────┘     │ (selected only)│           │
              │          └───────┬────────┘           │
    ┌─────────┼─────────┐       │                    │
    ▼         ▼         ▼       ▼                    ▼
FINANCIAL COMPETITOR MARKET   SYNTHESIZE       SYNTHESIZE
 AGENT     AGENT    INTEL    FOLLOW-UP        FOLLOW-UP
(yfinance) (Tavily) (Tavily)  (focused)    (from cached context)
    │         │       │         │                    │
    └─────────┼───────┘         │                    │
              ▼                 ▼                    ▼
       FULL REPORT      CONVERSATIONAL        CONVERSATIONAL
                          RESPONSE              RESPONSE
```

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

### 2. Get API Keys

- **Anthropic**: https://console.anthropic.com/
- **Tavily**: https://tavily.com (free tier: 1000 req/month)

### 3. Run

```bash
# Command line
python src/main.py "Compare Cisco's observability to DataDog and Dynatrace"

# Web UI
streamlit run ui/app.py
```

## Test Data Sources

```bash
# yfinance (no API key needed)
python -c "
import yfinance as yf
for ticker in ['DDOG', 'DT', 'CSCO']:
    t = yf.Ticker(ticker)
    print(f'{ticker}: {t.info.get(\"shortName\")} - MCap: {t.info.get(\"marketCap\")}')"

# Tavily (needs API key)
python -c "
import os
from tavily import TavilyClient
client = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
r = client.search('DataDog observability platform')
print(f'Found {len(r[\"results\"])} results')"
```

## Project Structure

```
src/
├── agents/              # Agent implementations
│   ├── manager.py       # Orchestrator with route node (new/followup routing)
│   ├── followup.py      # Follow-up routing, task building, synthesis
│   ├── financial.py     # Financial analysis agent (yfinance)
│   ├── competitor.py    # Competitor research agent (Tavily)
│   └── market_intel.py  # Market intelligence agent (Tavily)
├── tools/               # Data source integrations
│   ├── yfinance_tools.py
│   └── tavily_tools.py
├── prompts/             # Agent system prompts
│   ├── manager_prompt.py
│   ├── financial_prompt.py
│   ├── competitor_prompt.py
│   ├── market_intel_prompt.py
│   └── followup_prompt.py   # Route, synthesis, and task templates
├── report/              # Report generation
│   ├── generator.py
│   └── decision_tree.py
├── utils/
│   └── retry.py         # Retry with backoff (tenacity)
├── config.py            # Configuration
├── errors.py            # Custom exceptions
├── logging_config.py    # structlog JSON logging
└── main.py              # Entry point

ui/
└── app.py               # Streamlit interface (with follow-up support)

tests/
├── conftest.py          # Shared fixtures
├── unit/                # 126 unit tests
│   ├── test_followup.py       # Follow-up routing tests
│   ├── test_manager_agent.py  # Manager + follow-up path tests
│   └── ...
└── integration/         # 5 pipeline tests
```

## Tech Stack

- **Agent Framework**: LangGraph (Deep Agents pattern)
- **LLM**: Claude 3.5 Sonnet
- **Financials**: yfinance
- **Research**: Tavily
- **Frontend**: Streamlit

## License

MIT
