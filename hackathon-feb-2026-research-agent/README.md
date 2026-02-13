# Research Agent Team

A multi-agent research system using orchestrator pattern for business and competitor analysis.

## Demo Goal

Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace.

## Architecture

```
                         USER INPUT
                             │
                             ▼
                      MANAGER AGENT
                   (parses, delegates, synthesizes)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
    FINANCIAL AGENT                  COMPETITOR AGENT
    (yfinance)                       (Tavily search)
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                     SYNTHESIZED REPORT
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
├── agents/           # Agent implementations
│   ├── manager.py    # Orchestrator agent
│   ├── financial.py  # Financial analysis agent
│   └── competitor.py # Competitor research agent
├── tools/            # Data source integrations
│   ├── yfinance_tools.py
│   └── tavily_tools.py
├── prompts/          # Agent system prompts
├── report/           # Report generation
├── config.py         # Configuration
└── main.py           # Entry point

ui/
└── app.py            # Streamlit interface

tests/
├── test_tools.py
└── test_agents.py
```

## Tech Stack

- **Agent Framework**: LangGraph (Deep Agents pattern)
- **LLM**: Claude 3.5 Sonnet
- **Financials**: yfinance
- **Research**: Tavily
- **Frontend**: Streamlit

## License

MIT
