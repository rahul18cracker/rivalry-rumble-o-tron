# Research Agent Team - POST-HACKATHON ROADMAP

> **Context**: This document contains the long-term vision and improvements for AFTER the hackathon.
> For the hackathon itself, see `hackathon-plan.md`

---

## Hackathon Baseline (What we built)

```
Streamlit UI → Manager Agent → [Financial Agent, Competitor Agent] → Markdown Report
```

**Capabilities at hackathon end:**
- Single segment comparison (Observability)
- 3 companies (Cisco/Splunk, DataDog, Dynatrace)
- Basic financials (yfinance)
- Web research (Tavily)
- Markdown report output

---

## Phase 1: Stabilization (Week 1-2 Post-Hackathon)

### Goals
- [ ] Robust error handling and retry logic
- [ ] Caching layer for API responses (Redis or file-based)
- [ ] Comprehensive test coverage (>70%)
- [ ] Documentation and setup guide
- [ ] Clean up hackathon code debt

### Technical Debt to Address
- [ ] Proper async/await for parallel agent execution
- [ ] Structured logging throughout (use `structlog`)
- [ ] Environment-based configuration
- [ ] CI/CD pipeline setup
- [ ] Type hints throughout codebase

### Files to Create/Update
```
├── src/
│   ├── cache/
│   │   ├── __init__.py
│   │   └── response_cache.py     # Cache layer
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py             # Structured logging
│   │   └── retry.py              # Retry with backoff
│   └── config.py                  # Expand config management
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI pipeline
└── docs/
    └── setup.md                   # Setup guide
```

---

## Phase 2: Quality & Evaluation (Week 3-4)

### Agent Quality Evaluators
<!-- MARKER: EVALUATOR_SYSTEM -->

**Purpose:** Ensure agent outputs meet quality standards before synthesis

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVALUATOR ARCHITECTURE                        │
│                                                                  │
│  Sub-Agent Output → Evaluator Agent → Score + Feedback          │
│                          │                                       │
│                          ├── Factual Accuracy (can we verify?)  │
│                          ├── Completeness (all fields filled?)  │
│                          ├── Source Quality (reliable sources?) │
│                          └── Relevance (answers the question?)  │
│                                                                  │
│  If score < threshold → Request retry with feedback             │
└─────────────────────────────────────────────────────────────────┘
```

**Evaluation Rubric:**
| Criterion | Weight | Pass Threshold |
|-----------|--------|----------------|
| Factual Accuracy | 30% | All cited data verifiable |
| Completeness | 25% | No required fields empty |
| Source Quality | 25% | ≥80% from reliable sources |
| Relevance | 20% | Answers the actual question |

**Implementation Tasks:**
- [ ] Define evaluation rubric in code
- [ ] Implement Evaluator agent with structured output
- [ ] Add retry loop with feedback for failed evaluations
- [ ] Track evaluation metrics over time
- [ ] Dashboard for evaluation scores

**New Files:**
```
├── src/agents/
│   └── evaluator.py              # Evaluator agent
├── src/evaluation/
│   ├── __init__.py
│   ├── rubric.py                 # Scoring criteria
│   └── metrics.py                # Track scores over time
```
<!-- END MARKER: EVALUATOR_SYSTEM -->

### Critique Agent
<!-- MARKER: CRITIQUE_AGENT -->

**Purpose:** Challenge findings, identify gaps, suggest deeper research

```python
# Critique agent responsibilities
- Question assumptions in the analysis
- Identify missing competitive factors
- Suggest alternative interpretations
- Flag potential biases in sources
- Recommend areas for deeper research
```

**Integration Flow:**
```
Manager synthesizes draft report
        ↓
Critique Agent reviews draft
        ↓
Returns: {
    "issues_found": [...],
    "missing_perspectives": [...],
    "suggested_deeper_research": [...],
    "confidence_score": 0.85
}
        ↓
Manager addresses issues OR flags for user
        ↓
Final report
```

**Implementation Tasks:**
- [ ] Design critique prompt template
- [ ] Integrate into synthesis step (Manager calls Critique before final report)
- [ ] Allow user to request "deeper analysis" triggering critique
- [ ] Store critique feedback for prompt improvement

**New Files:**
```
├── src/agents/
│   └── critique.py               # Critique agent
├── src/prompts/
│   └── critique_prompt.py        # Critique prompts
```
<!-- END MARKER: CRITIQUE_AGENT -->

---

## Phase 3: Expanded Capabilities (Month 2)

### Additional Data Sources
<!-- MARKER: DATA_SOURCES -->

| Source | Purpose | Priority | API Cost |
|--------|---------|----------|----------|
| **SEC Edgar** | Full 10-K/10-Q parsing | P0 | Free |
| **Glassdoor API** | Employee sentiment, culture | P1 | Paid |
| **LinkedIn API** | Hiring trends, headcount | P1 | Paid |
| **Crunchbase** | Funding, acquisitions | P2 | Paid |
| **G2/Gartner** | Product reviews, ratings | P2 | Paid |
| **Patent databases** | Innovation tracking | P3 | Free/Paid |
| **GitHub API** | OSS activity, dev engagement | P3 | Free |
| **News APIs** | Real-time news sentiment | P2 | Freemium |

**Implementation Pattern:**
```python
# Abstract data source interface
class DataSource(ABC):
    @abstractmethod
    def search(self, query: str) -> List[Dict]: pass

    @abstractmethod
    def get_company_data(self, company: str) -> Dict: pass

    @property
    @abstractmethod
    def rate_limit(self) -> int: pass

# Each source implements this interface
class GlassdoorSource(DataSource): ...
class LinkedInSource(DataSource): ...
```

**New Files:**
```
├── src/tools/
│   ├── base.py                   # DataSource ABC
│   ├── edgar.py                  # SEC Edgar (expand)
│   ├── glassdoor.py              # Glassdoor
│   ├── linkedin.py               # LinkedIn
│   ├── crunchbase.py             # Crunchbase
│   └── g2.py                     # G2 reviews
```
<!-- END MARKER: DATA_SOURCES -->

### Broader Scope Support
<!-- MARKER: SCOPE_EXPANSION -->

**Goal:** Support both narrow (segment) and broad (full company) analysis

```
User: "Compare Cisco to competitors"
        │
        ▼
┌─────────────────────────────────────────┐
│          SCOPE DETECTION AGENT          │
│                                         │
│  Analyzes request to determine:         │
│  - Broad (full company) vs Narrow (seg) │
│  - Which segments if narrow             │
│  - Which competitors to include         │
│  - Time range for analysis              │
└─────────────────────────────────────────┘
        │
        ├── Broad → Multi-segment parallel analysis
        │           [Networking, Security, Collab, Observability]
        │
        └── Narrow → Deep single-segment analysis
                    [Observability only]
```

**Company → Segment Mapping Database:**
```yaml
# data/company_segments.yaml
cisco:
  segments:
    networking:
      products: ["Catalyst", "Nexus", "Meraki"]
      competitors: ["Arista", "Juniper", "HPE"]
    security:
      products: ["Umbrella", "Duo", "SecureX"]
      competitors: ["Palo Alto", "CrowdStrike", "Fortinet"]
    collaboration:
      products: ["Webex", "Vidyo"]
      competitors: ["Zoom", "Microsoft Teams", "Slack"]
    observability:
      products: ["Splunk", "AppDynamics", "ThousandEyes"]
      competitors: ["DataDog", "Dynatrace", "New Relic"]

datadog:
  segments:
    observability:
      products: ["APM", "Infrastructure", "Logs", "RUM", "Security"]
      competitors: ["Dynatrace", "Splunk", "New Relic"]
```

**Implementation Tasks:**
- [ ] Build company → segment mapping database
- [ ] Implement Scope Detection agent
- [ ] Support dynamic competitor identification
- [ ] Allow user to adjust scope mid-analysis
- [ ] Parallel execution for multi-segment

**New Files:**
```
├── data/
│   └── company_segments.yaml     # Segment mappings
├── src/agents/
│   └── scope_detector.py         # Scope detection
```
<!-- END MARKER: SCOPE_EXPANSION -->

---

## Phase 4: Advanced Features (Month 3+)

### Interactive Refinement
<!-- MARKER: INTERACTIVE -->

**Goal:** User can drill down, ask follow-ups, challenge findings

```
User: "Why do you say DataDog has stronger integrations?"

Agent: "Based on my research, DataDog lists 750+ integrations
        on their website [source], while Dynatrace lists ~600
        [source]. However, I should note that integration count
        doesn't capture quality or depth. Would you like me to
        compare specific integration categories?"

User: "Yes, compare cloud provider integrations specifically"

Agent: [Triggers focused sub-research on cloud integrations]
```

**Implementation:**
- Conversation memory with full report context
- Follow-up query routing to appropriate sub-agent
- "Challenge this finding" button that triggers deeper research
- Citation drill-down (click source → see full context)

**New Files:**
```
├── src/
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── conversation.py       # Conversation history
│   │   └── report_context.py     # Keep report in context
│   └── agents/
│       └── followup_router.py    # Route follow-ups
```
<!-- END MARKER: INTERACTIVE -->

### Automated Monitoring
<!-- MARKER: MONITORING -->

**Goal:** Track companies over time, alert on significant changes

```
User sets up: "Monitor Cisco vs DataDog quarterly"

System:
├── Runs analysis quarterly (or on schedule)
├── Compares to previous analysis
├── Detects significant changes:
│   ├── Revenue change >10%
│   ├── New product launches
│   ├── Acquisitions
│   └── Leadership changes
├── Generates diff report
└── Sends alert (email/Slack)
```

**Implementation Tasks:**
- [ ] Scheduled job infrastructure (Celery or APScheduler)
- [ ] Diff engine for report comparison
- [ ] Alert/notification system
- [ ] Historical report storage
- [ ] Comparison UI (side-by-side diffs)

**New Files:**
```
├── src/
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── jobs.py               # Scheduled analysis jobs
│   ├── diff/
│   │   ├── __init__.py
│   │   └── report_diff.py        # Report comparison
│   └── notifications/
│       ├── __init__.py
│       ├── email.py              # Email alerts
│       └── slack.py              # Slack alerts
├── data/
│   └── historical_reports/       # Stored reports
```
<!-- END MARKER: MONITORING -->

### Multi-Modal Reports
<!-- MARKER: MULTIMODAL -->

**Goal:** Rich reports with dynamic visualizations

**Features:**
- [ ] Interactive charts (Plotly/Altair)
- [ ] Exportable to PDF
- [ ] Exportable to PowerPoint
- [ ] Embeddable widgets for Confluence/Notion
- [ ] Voice summary generation (TTS)
- [ ] Executive summary video (stretch)

**Implementation:**
```python
# Report export interface
class ReportExporter(ABC):
    @abstractmethod
    def export(self, report: Report, format: str) -> bytes: pass

class PDFExporter(ReportExporter): ...
class PowerPointExporter(ReportExporter): ...
class ConfluenceExporter(ReportExporter): ...
```

**New Files:**
```
├── src/report/
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── base.py               # Exporter ABC
│   │   ├── pdf.py                # PDF export
│   │   ├── pptx.py               # PowerPoint export
│   │   └── confluence.py         # Confluence wiki
│   └── visualizations/
│       ├── __init__.py
│       └── charts.py             # Interactive charts
```
<!-- END MARKER: MULTIMODAL -->

---

## Phase 5: Enterprise Features (Quarter 2+)

<!-- MARKER: ENTERPRISE -->

### Multi-Tenancy & Access Control
- [ ] User authentication (OAuth/SSO)
- [ ] Team workspaces
- [ ] Report sharing and permissions
- [ ] Audit logging
- [ ] Usage quotas per team

### Custom Knowledge Base
- [ ] Upload internal documents (strategy docs, competitive intel)
- [ ] RAG pipeline for internal knowledge
- [ ] Blend internal + external research
- [ ] Citation of internal sources

### API & Integrations
- [ ] REST API for programmatic access
- [ ] Slack integration (slash commands)
- [ ] Microsoft Teams integration
- [ ] Salesforce integration (account research)
- [ ] CRM enrichment pipeline
- [ ] Webhooks for external triggers

### Architecture at Scale
```
                    ┌─────────────────┐
                    │   Web App UI    │
                    │   (React/Next)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    API Gateway  │
                    │   (FastAPI)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌───────▼───────┐ ┌────────▼────────┐
│  Auth Service   │ │ Research Svc  │ │ Scheduler Svc   │
│  (Users/Teams)  │ │ (Agents)      │ │ (Monitoring)    │
└─────────────────┘ └───────┬───────┘ └─────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
           ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
           │Manager │  │Financ. │  │Compet. │
           │Agent   │  │Agent   │  │Agent   │
           └────────┘  └────────┘  └────────┘
                            │
                   ┌────────▼────────┐
                   │  Data Layer     │
                   │  (PostgreSQL,   │
                   │   Redis, S3)    │
                   └─────────────────┘
```

<!-- END MARKER: ENTERPRISE -->

---

## Success Metrics (Long-term)

<!-- MARKER: METRICS -->

| Metric | Phase 2 Target | Phase 4 Target | How to Measure |
|--------|----------------|----------------|----------------|
| **Research Accuracy** | >75% | >90% | Human eval sample |
| **Time Savings** | 5x faster | 10x faster | Compare to manual |
| **User Satisfaction** | >4.0/5 | >4.5/5 | Post-report survey |
| **Source Coverage** | 5+ sources | 15+ sources | Automated count |
| **Report Completion** | >90% | >98% | Track failures |
| **Response Time** | <5 min | <2 min | P95 latency |

<!-- END MARKER: METRICS -->

---

## Version Roadmap

| Version | Timeline | Key Features |
|---------|----------|--------------|
| 0.1.0 | Hackathon | Initial POC - 2 agents, basic UI |
| 0.2.0 | +2 weeks | Stabilization, error handling, caching |
| 0.3.0 | +1 month | Evaluators, critique agent |
| 0.4.0 | +2 months | Additional data sources, scope expansion |
| 0.5.0 | +3 months | Interactive refinement, monitoring |
| 1.0.0 | +4 months | Production-ready, enterprise features |

---

## File Markers Reference

When implementing features, search for these markers in this document:

| Marker | Section | Purpose |
|--------|---------|---------|
| `EVALUATOR_SYSTEM` | Phase 2 | Quality evaluation architecture |
| `CRITIQUE_AGENT` | Phase 2 | Critique agent design |
| `DATA_SOURCES` | Phase 3 | Additional data source list |
| `SCOPE_EXPANSION` | Phase 3 | Broad vs narrow analysis |
| `INTERACTIVE` | Phase 4 | Follow-up conversation |
| `MONITORING` | Phase 4 | Automated tracking |
| `MULTIMODAL` | Phase 4 | Rich report formats |
| `ENTERPRISE` | Phase 5 | Enterprise features |
| `METRICS` | Metrics | Success metrics |

---

*Created: 2026-02-13*
*For hackathon execution, see: `hackathon-plan.md`*
