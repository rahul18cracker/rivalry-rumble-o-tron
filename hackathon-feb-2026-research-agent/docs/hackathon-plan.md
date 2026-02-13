# Research Agent Team - HACKATHON PLAN (Days 1-2)

> **Focus**: This document contains ONLY what you need for the 1-2 day hackathon.
> Post-hackathon roadmap is in `post-hackathon-roadmap.md`

---

## Context

**Problem**: Manual business and competitor analysis is time-consuming and inconsistent.

**Solution**: Multi-agent research system using orchestrator pattern.

**Demo Goal**: Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace.

---

## 1. Top 5 Goals (Priority Order)

| # | Goal | Success Criteria | Owner |
|---|------|------------------|-------|
| 1 | **Working Multi-Agent Orchestration** | Manager delegates to sub-agents, synthesizes results | P1 |
| 2 | **Real Data Integration** | yfinance + Tavily return actual company data | P2, P3 |
| 3 | **Coherent Analysis Output** | Report compares 3 companies with actual metrics | All |
| 4 | **Interactive User Experience** | User inputs query via chat UI, receives analysis | P3 |
| 5 | **Team Collaboration Success** | 3 teammates work in parallel without blocking | All |

---

## 2. Scope Boundaries

### ✅ IN SCOPE (Must Have)
- Orchestrator pattern: Manager + 2 sub-agents
- Observability segment: Cisco/Splunk vs DataDog vs Dynatrace
- Financial metrics: revenue, growth, market cap
- Basic competitive positioning
- Markdown report with sections
- Simple Streamlit chat UI
- Basic progress visibility

### 🎯 IN SCOPE (Should Have - if time permits)
- Charts/visualizations (revenue comparison)
- User Q&A refinement
- Source citations in report
- 3rd sub-agent (Market Intelligence)

### ❌ OUT OF SCOPE (Post-Hackathon)
- Evaluators / Critique agent
- Error recovery / retry logic
- Caching layer
- Multiple segment support
- Enterprise features

---

## 3. Technical Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| **Agent Framework** | Deep Agents (LangGraph) | [Example repo](https://github.com/ALucek/deep-agents-walkthrough/tree/main/competitive_analysis_agent) |
| **LLM** | Claude 3.5 Sonnet | via Anthropic API |
| **Financials** | yfinance | No API key needed |
| **Research** | Tavily | Free tier: 1000 req/month |
| **Frontend** | Streamlit | Pure Python, fast iteration |
| **Language** | Python 3.11+ | |

### API Keys Required
```bash
# .env file
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here  # tavily.com (free)
```

---

## 4. Project Structure

```
hackathon-feb-2026-research-agent/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── manager.py          # [Person 1]
│   │   ├── financial.py        # [Person 2]
│   │   ├── competitor.py       # [Person 3]
│   │   └── .claude-skills.md   # Debug guide
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── yfinance_tools.py   # [Person 2]
│   │   ├── tavily_tools.py     # [Person 3]
│   │   └── .claude-skills.md   # Debug guide
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── manager_prompt.py
│   │   ├── financial_prompt.py
│   │   └── competitor_prompt.py
│   │
│   └── report/
│       ├── __init__.py
│       ├── generator.py
│       └── templates.py
│
├── ui/
│   ├── app.py                  # Streamlit [Person 3]
│   └── .claude-skills.md       # Debug guide
│
└── tests/
    ├── test_tools.py
    └── test_agents.py
```

---

## 5. Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│  "Compare Cisco's observability portfolio to DataDog & Dynatrace"│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MANAGER AGENT [P1]                          │
│  - Parses user request                                          │
│  - Creates task breakdown (todo list)                           │
│  - Delegates to sub-agents (parallel)                           │
│  - Synthesizes final report                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│   FINANCIAL AGENT [P2]    │     │   COMPETITOR AGENT [P3]   │
│                           │     │                           │
│   Tools:                  │     │   Tools:                  │
│   - yfinance              │     │   - Tavily search         │
│                           │     │                           │
│   Output:                 │     │   Output:                 │
│   - Revenue, growth       │     │   - Products, positioning │
│   - Market cap, margins   │     │   - Strengths/weaknesses  │
└───────────────────────────┘     └───────────────────────────┘
            │                                   │
            └─────────────────┬─────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SYNTHESIZED REPORT                          │
│  - Executive Summary                                            │
│  - Financial Comparison                                         │
│  - Competitive Analysis                                         │
│  - Key Insights                                                 │
│  - Sources                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent Output Schemas

### Financial Agent Output
```python
{
    "company": "DataDog",
    "ticker": "DDOG",
    "metrics": {
        "market_cap": "$45B",
        "revenue_ttm": "$2.1B",
        "revenue_growth_yoy": "25%",
        "gross_margin": "80%"
    },
    "historical_revenue": [
        {"year": 2022, "revenue": 1.3},
        {"year": 2023, "revenue": 1.7},
        {"year": 2024, "revenue": 2.1}
    ],
    "sources": ["yfinance"]
}
```

### Competitor Agent Output
```python
{
    "company": "DataDog",
    "products": ["APM", "Infrastructure", "Logs", "RUM"],
    "target_market": "Cloud-native enterprises",
    "pricing_model": "Usage-based",
    "strengths": ["Unified platform", "Strong integrations"],
    "weaknesses": ["Expensive at scale"],
    "sources": ["tavily:datadog.com", "tavily:g2.com"]
}
```

---

## 7. Team Task Breakdown

### Day 1

| Person | Morning (4 hrs) | Afternoon (4 hrs) |
|--------|-----------------|-------------------|
| **P1** | Set up repo, project structure, Deep Agents scaffolding | Implement Manager agent with task delegation |
| **P2** | Implement yfinance tools, test with DDOG/CSCO/DT | Implement Financial agent, connect to Manager |
| **P3** | Set up Tavily, implement search tools | Implement Competitor agent, connect to Manager |

**Day 1 Milestone**: All 3 agents can be invoked individually and return structured data

### Day 2

| Person | Morning (4 hrs) | Afternoon (4 hrs) |
|--------|-----------------|-------------------|
| **P1** | Implement report synthesis, integrate outputs | Polish orchestration, handle edge cases |
| **P2** | Add charts data generation, improve prompts | Help with UI integration, testing |
| **P3** | Build Streamlit UI, chat interface | Integrate full flow, demo prep |

**Day 2 Milestone**: End-to-end demo working

### Git Workflow
```bash
# Branches
main                    # Protected - working code only
├── feature/manager     # P1
├── feature/financial   # P2
├── feature/competitor  # P3
└── feature/ui          # P3 (Day 2)

# Process: Feature branch → PR → Quick review → Merge
```

---

## 8. Quick Validation Commands

### Test Data Sources
```bash
# yfinance (no API key)
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

### Test Agents
```bash
# Financial agent
python -c "from src.agents.financial import financial_agent; print(financial_agent.run('Analyze DDOG'))"

# Competitor agent
python -c "from src.agents.competitor import competitor_agent; print(competitor_agent.run('Analyze DDOG'))"

# Full orchestration
python -c "from src.agents.manager import manager; print(manager.run('Compare DDOG to DT'))"
```

### Run UI
```bash
streamlit run ui/app.py
# If port 8501 busy: streamlit run ui/app.py --server.port 8502
```

---

## 9. Report Output Structure

```markdown
# Competitive Analysis: Observability Market
*Generated: 2026-02-14 | Research Agent v0.1*

## Executive Summary
[2-3 paragraphs of key findings]

## Companies Analyzed
| Company | Ticker | Observability Products |
|---------|--------|----------------------|
| Cisco (Splunk) | CSCO | Splunk O11y, AppDynamics |
| DataDog | DDOG | APM, Infra, Logs, RUM |
| Dynatrace | DT | Full-stack observability |

## Financial Comparison
[Table + optional chart]

## Competitive Analysis
[Product comparison, positioning, SWOT]

## Key Insights
1. [Insight 1]
2. [Insight 2]
3. [Insight 3]

## Sources
- [1] Yahoo Finance: DDOG data
- [2] Tavily: datadog.com/product
...
```

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Deep Agents learning curve | Reference [example repo](https://github.com/ALucek/deep-agents-walkthrough) heavily |
| API rate limits | Cache responses, use mock data for dev |
| Integration issues Day 2 | Test interfaces early with shared schemas |
| Demo fails live | Pre-run analysis, have recorded backup |

---

## 11. Demo Script

### Setup (5 min before)
```bash
cd hackathon-feb-2026-research-agent
source venv/bin/activate
streamlit run ui/app.py
```

### Demo Flow (5 min)
1. **Show UI** - Clean chat interface
2. **Enter query**: "Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace"
3. **Show progress** - Task list updating
4. **Show report** - Scroll through sections
5. **Follow-up** (if time): "Tell me more about DataDog's pricing"

### Backup
- Pre-generated report ready
- Screenshots as fallback slides

---

## 12. Claude Skills Files (Debug Guides)

Each directory should have a `.claude-skills.md` for debugging. Key content for each:

### `src/agents/.claude-skills.md`
- Agent inventory table
- How to test each agent individually
- Output schema reference
- Common orchestration issues

### `src/tools/.claude-skills.md`
- API key requirements
- Rate limits
- How to test each data source
- Mock data for offline development

### `ui/.claude-skills.md`
- Streamlit session state debugging
- Progress indicator patterns
- Common UI issues

---

## Quick Start Checklist

### Setup (P1 does first, others pull)
- [ ] Create repo structure
- [ ] Create requirements.txt with dependencies
- [ ] Create .env.example
- [ ] Set up .gitignore
- [ ] Create base files with `pass` placeholder

### Validation Points
- [ ] **Hour 2**: All tools return data for DDOG
- [ ] **Hour 4**: Each agent runs standalone
- [ ] **Hour 8 (End Day 1)**: Manager can call sub-agents
- [ ] **Hour 12**: Report generates from agent outputs
- [ ] **Hour 14**: UI triggers full flow
- [ ] **Hour 16 (End Day 2)**: Demo ready

---

*Plan created: 2026-02-13*
*For post-hackathon roadmap, see: `post-hackathon-roadmap.md`*
