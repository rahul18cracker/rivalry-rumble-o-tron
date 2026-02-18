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
src/agents/manager.py      — Orchestrator (structured callbacks, asyncio.gather)
src/agents/financial.py    — yfinance tools (Number Cruncher)
src/agents/competitor.py   — Tavily tools (Street Scout)
src/tools/yfinance_tools.py
src/tools/tavily_tools.py
src/report/generator.py    — LLM report synthesis
src/report/decision_tree.py — Text tree for Behind the Scenes
src/config.py              — Config and API key management
ui/app.py                  — Streamlit UI
docs/skills-learned.md     — 12 detailed technical learnings
docs/post-hackathon-roadmap.md — Observability plan
SESSION.md                 — Session context and history
```

## Setup

```bash
source venv/bin/activate
python -c "from src.config import get_config; print('OK' if not get_config().validate() else 'Missing keys')"
streamlit run ui/app.py
```

Requires `.env` with: `OPENAI_API_KEY`, `TAVILY_API_KEY`.

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

## Remaining TODOs

- Test error handling (missing keys, API failures)
- Add caching for API responses
- Consider 3rd Market Intelligence sub-agent
- Production observability (LangSmith, cost tracking, quality scoring — see docs/post-hackathon-roadmap.md)
