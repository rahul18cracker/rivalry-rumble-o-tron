# Project: Rivalry Rumble-o-Tron

Multi-agent competitive research system built with LangGraph, LangChain, and Streamlit.

## Architecture

- **Manager Agent** (`src/agents/manager.py`) — Orchestrator. Parses queries, dispatches sub-agents in parallel via `asyncio.gather`, synthesizes final report.
- **Number Cruncher** (`src/agents/financial.py`) — Financial sub-agent using yfinance tools.
- **Street Scout** (`src/agents/competitor.py`) — Competitive intelligence sub-agent using Tavily search tools.
- **Report Generator** (`src/report/generator.py`) — LLM-powered markdown report synthesis.
- **Decision Tree** (`src/report/decision_tree.py`) — Text tree visualization for Behind the Scenes UI.
- **Streamlit UI** (`ui/app.py`) — Chat interface with progress indicators, example query cards, Behind the Scenes expander.

## Key Files

```
src/agents/manager.py      — Orchestrator (error handling, timeout, partial failures)
src/agents/financial.py    — yfinance tools (Number Cruncher)
src/agents/competitor.py   — Tavily tools (Street Scout)
src/tools/yfinance_tools.py — Input validation, retry, logging
src/tools/tavily_tools.py  — Input validation, retry, logging
src/utils/retry.py         — retry_transient() decorator (tenacity)
src/report/generator.py    — LLM report synthesis with fallback
src/report/decision_tree.py — Text tree for Behind the Scenes
src/config.py              — Config, API keys, LangSmith tracing
src/errors.py              — Custom exception hierarchy
src/logging_config.py      — structlog JSON configuration
ui/app.py                  — Streamlit UI
tests/conftest.py          — Shared fixtures, singleton reset, LLM/tool mocks
tests/unit/               — 94 unit tests (all mocked, no API keys)
tests/integration/        — 5 pipeline tests (full flow, partial failures)
.env.example              — Documented env vars (including LangSmith)
docs/skills-learned.md     — 20 detailed technical learnings
docs/post-hackathon-roadmap.md — Observability plan
SESSION.md                 — Session context and history
```

## Setup

```bash
source venv/bin/activate
pip install -e ".[dev]"
python -c "from src.config import get_config; print('OK' if not get_config().validate() else 'Missing keys')"
streamlit run ui/app.py
```

Requires `.env` with: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`. Optional: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGSMITH_PROJECT` for LangSmith tracing.

## Testing

```bash
# Run all tests (no API keys needed)
pytest tests/ -v -m "not api" --cov=src --cov-report=term-missing

# Lint
ruff check src/ tests/
ruff format --check src/ tests/
```

## Technical Learnings (Apply These)

### LangGraph

1. **Message format**: Always use LangChain message objects (`SystemMessage`, `HumanMessage`), never raw dicts. Use `Annotated[list, add_messages]` for state fields.
2. **Thread safety**: LangGraph runs sync nodes in a thread pool via `run_in_executor()`. Callbacks may fire from any thread. Design callbacks to only mutate shared data structures — never call Streamlit from a callback.
3. **Tool call extraction**: Don't add custom logging wrappers. Walk the message list: `AIMessage.tool_calls` has `{id, name, args}`, match to `ToolMessage.tool_call_id` for results.
4. **Agent return types**: Always return structured dicts from agent entry points, not plain strings. A dict is extensible without breaking callers.

### Streamlit + Async

5. **NoSessionContext fix**: Streamlit placeholders are NOT thread-safe for writes. Run the agent in a worker thread (`threading.Thread` + `asyncio.new_event_loop()`), use a shared dict as bridge, poll from the main thread with `thread.join(timeout=1.0)`.
6. **Rerun behavior**: After `process_query()`, call `st.rerun()`. Everything must be in `st.session_state.messages` before rerun or it's lost. Render all rich UI (expanders, charts) from session state in `display_chat_history()`.
7. **Progress UI**: Use `st.empty()` placeholders + `st.progress()`. Structured callbacks (`{"stage": "...", "status": "running", "detail": "..."}`) enable per-stage rendering.

### Visualization

8. **Text trees over Graphviz**: `st.graphviz_chart()` becomes unreadable at 10+ nodes. Use `st.code(text, language=None)` with box-drawing characters and emojis instead. Scales naturally, no zoom issues.

### General

9. **Parallel agents**: Use `asyncio.gather()` for concurrent sub-agent execution. Use a plain `async def _noop(): return None` as fallback (not deprecated `asyncio.coroutine`).
10. **Tavily init**: Always `load_dotenv()` at the top of tool modules. Don't rely on it being loaded elsewhere.
11. **Metadata in session state**: Store agent metadata (companies, tickers, tool calls, elapsed time) alongside messages for rich post-run UI like the Behind the Scenes expander.

### Error Handling & Testing

12. **Partial failure with gather**: Use `asyncio.gather(return_exceptions=True)` so one agent failing doesn't kill the other. Check results with `isinstance(result, BaseException)`. Wrap in `asyncio.wait_for(timeout=120)`.
13. **Graceful degradation**: Each pipeline stage should degrade, not crash. Report generator falls back from LLM synthesis to basic template. Manager returns error dict instead of raising.
14. **Singleton reset in tests**: Module-level agent caches (`_financial_agent`, etc.) leak between tests. Use autouse fixture to reset all singletons before each test.
15. **Mock at the right level**: For agent tests, patch `get_financial_agent()` with AsyncMock. For manager tests, patch `run_financial_agent` directly. Never mock LangGraph internals.
16. **structlog for agents**: Use dotted event names (`manager.parse.start`, `financial_agent.run.error`) for easy grep filtering across concurrent agents.
17. **ruff per-file-ignores**: Prompt template files have long string literals that can't be reformatted. Use `[tool.ruff.lint.per-file-ignores]` for E501 on those files.

### Retry & Observability

18. **Retry inner-helper pattern**: Can't stack `@retry` on `@tool` — extract API call into a plain function with `@retry_transient()`, keep `@tool` as thin validation + error-dict shell.
19. **LangSmith tracing**: LangGraph auto-traces when `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` are set. No code changes in agents — just set env vars before agent creation.
20. **GitHub Actions location**: Workflows must be at `.github/workflows/` relative to the **git repo root** — not in a subdirectory. Use `defaults.run.working-directory` for monorepo layouts.

## Remaining TODOs

- Add caching for API responses
- Consider 3rd Market Intelligence sub-agent
- Production observability (cost tracking, quality scoring — see docs/post-hackathon-roadmap.md)
