# Skills Learned - Research Agent Team

Technical learnings accumulated while building the multi-agent research system.

---

## 1. LangGraph Message Format

**Problem**: LangGraph agents crashed with cryptic errors when using plain dicts for messages.

**Root Cause**: LangGraph's `add_messages` reducer expects LangChain message objects, not raw dicts.

**Fix**:
```python
# Wrong
messages = [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

# Correct
from langchain_core.messages import SystemMessage, HumanMessage
messages = [SystemMessage(content="..."), HumanMessage(content="...")]
```

**Also**: Use `Annotated[list, add_messages]` for the messages field in state TypedDicts so LangGraph properly merges message lists across nodes.

---

## 2. Streamlit + Async + Threading (NoSessionContext)

**Problem**: `streamlit.errors.NoSessionContext` when trying to update Streamlit placeholders from an async agent callback.

**Root Cause**: Two compounding issues:
1. `asyncio.run()` fails inside Streamlit because Streamlit's script runner thread may already have an event loop.
2. Running the async agent in a worker thread (via `threading.Thread` + `asyncio.new_event_loop()`) works for the agent, but the progress callback fires from that worker thread. Streamlit requires all UI writes to happen from the script runner thread that owns the session context.

**Fix — Polling Pattern**:
```python
# Shared mutable state (written by worker, read by main)
stage_states = {}

def progress_callback(update):
    # Only mutate shared data — NO Streamlit calls here
    stage_states[update["stage"]] = {"status": update["status"], ...}

def _run_agent():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result[0] = loop.run_until_complete(run_manager_agent(query, progress_callback))
    loop.close()

thread = threading.Thread(target=_run_agent, daemon=True)
thread.start()

# Poll from main thread — Streamlit writes are safe here
while thread.is_alive():
    thread.join(timeout=1.0)
    stages_placeholder.markdown(render_stage_text(stage_states))  # safe
    progress_bar.progress(compute_progress(stage_states))         # safe
```

**Key Insight**: Streamlit placeholders (`st.empty()`, `st.progress()`) are NOT thread-safe for writes. Always update them from the script runner thread. Use a shared dict as the bridge between the worker and UI threads.

---

## 3. LangGraph Node Thread Pool

**Problem**: Even within `asyncio`, LangGraph runs sync node functions (like `parse_request`) in a thread pool executor via `run_in_executor()`.

**Implication**: A callback passed through LangGraph state and called from a sync node will execute in LangGraph's thread pool thread — not the thread that created the coroutine. This is why the Streamlit `NoSessionContext` error appeared even though the agent was invoked from a seemingly controlled thread.

**Lesson**: Never assume which thread a callback will fire from when using LangGraph. Always design callbacks to be thread-safe (e.g., only mutate shared data structures).

---

## 4. Parallel Agent Execution with asyncio.gather

**Problem**: Financial and Competitor agents were running sequentially (await one, then await the other), doubling the execution time.

**Fix**: Use `asyncio.gather()` to run both concurrently:
```python
async def _noop():
    return None

financial_results, competitor_results = await asyncio.gather(
    financial_task if financial_task else _noop(),
    competitor_task if competitor_task else _noop(),
)
```

**Note**: `asyncio.coroutine` is deprecated in Python 3.10+. Use a plain `async def` for no-op coroutines.

---

## 5. Streamlit Progress UI Patterns

**Pattern**: Multi-stage progress display using placeholders.

```python
progress_bar = st.progress(0.0)
stages_placeholder = st.empty()
elapsed_placeholder = st.empty()
result_placeholder = st.empty()

# During processing: update progress_bar, stages_placeholder, elapsed_placeholder
# On completion: .empty() the progress widgets, .markdown() the result
```

**Key Details**:
- `st.empty()` creates a single-element placeholder that can be overwritten
- `placeholder.empty()` clears the placeholder (removes from UI)
- `st.container()` groups multiple elements but `container.empty()` clears all children
- `st.progress(value)` accepts 0.0-1.0 float
- Use `time.sleep(0.5)` before collapsing progress so the user sees 100%

---

## 6. Streamlit Rerun Behavior

**Gotcha**: After `process_query()` completes, calling `st.rerun()` re-executes the entire script. The report must be stored in `st.session_state.messages` before rerun, otherwise it's lost.

**Pattern**:
```python
if prompt := st.chat_input("..."):
    process_query(prompt)      # stores result in st.session_state.messages
    st.rerun()                 # re-renders with updated state
```

The `display_chat_history()` function then renders all stored messages on each rerun.

---

## 7. Tavily API Key Loading

**Problem**: Tavily client initialization failed silently because `.env` wasn't loaded when the module was imported.

**Fix**: Add `load_dotenv()` at the top of `tavily_tools.py` before accessing environment variables. Don't rely on it being loaded elsewhere.

---

## 8. Structured Callbacks for Progress Tracking

**Pattern**: Instead of plain string callbacks, use structured dicts to enable richer UI:

```python
# Old: callback("Analyzing financial data...")
# New:
callback({
    "stage": "financial",       # maps to a pipeline stage
    "status": "running",        # pending | running | done
    "detail": "Fetching data"   # human-readable detail
})
```

This lets the UI maintain a state map of all stages and render each independently with appropriate icons and progress calculations.

---

## 9. Streamlit session_state Metadata for Rich Post-Run UI

**Problem**: A `st.expander("Behind the Scenes")` created during `process_query()` disappeared after `st.rerun()` because Streamlit re-executes the entire script from scratch on each rerun.

**Root Cause**: Any UI elements created during a function call are ephemeral — they only exist for that single script execution. After `st.rerun()`, only code that runs unconditionally (or based on `st.session_state`) will produce visible elements.

**Fix**: Store metadata alongside the message in `st.session_state.messages`, then render the expander in `display_chat_history()` which runs on every script execution:

```python
# During process_query — store metadata with the message
st.session_state.messages.append({
    "role": "assistant",
    "content": report,
    "metadata": {
        "companies": [...],
        "tickers": [...],
        "elapsed": elapsed,
        "financial_results": {"message_count": 7, "tickers": [...]},
        "competitor_results": {"message_count": 13, "companies": [...]},
    },
})

# In display_chat_history — render from session state (survives rerun)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        meta = message.get("metadata")
        if meta and message["role"] == "assistant":
            with st.expander("Behind the Scenes"):
                # render agent stats from meta
```

**Lesson**: In Streamlit, anything that must survive a rerun must be in `st.session_state`. Design your data model so all rich UI elements (expanders, charts, tables) can be reconstructed from session state alone.

---

## 10. Agent Return Type Design — Dict Over String

**Problem**: `run_manager_agent()` originally returned just the report string. When the UI needed agent metadata (companies, tickers, LLM round-trips) for the "Behind the Scenes" expander, there was no way to access it.

**Fix**: Changed the return type from `str` to `dict`:

```python
# Before
async def run_manager_agent(query, callback) -> str:
    ...
    return result["final_report"]

# After
async def run_manager_agent(query, callback) -> dict:
    ...
    return {
        "final_report": result["final_report"],
        "companies": result.get("companies", []),
        "tickers": result.get("tickers", []),
        "financial_results": result.get("financial_results"),
        "competitor_results": result.get("competitor_results"),
    }
```

**Lesson**: Design agent entry points to return structured dicts from the start, even if you only need one field today. Adding metadata later requires changing every caller. A dict is extensible without breaking the contract.

---

## 11. Extracting Tool Calls from LangGraph Message History

**Problem**: Needed to show which tools each sub-agent called (with arguments) in the UI, but LangGraph doesn't expose a built-in tool call log.

**Insight**: LangGraph already records everything in the messages list. `AIMessage` objects have a `.tool_calls` attribute (list of `{id, name, args}`), and each `ToolMessage` has a `.tool_call_id` that matches back to the call.

**Fix**: Walk the message list, match AIMessage tool calls to ToolMessage responses by ID:

```python
def _extract_tool_calls(messages):
    pending = {}
    tool_calls = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}
        if msg.__class__.__name__ == "ToolMessage":
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and call_id in pending:
                info = pending.pop(call_id)
                tool_calls.append({...info, "result_preview": msg.content[:200]})
    return tool_calls
```

**Lesson**: Don't add custom logging wrappers around tools when LangGraph already captures the data. Mine the message history instead.

---

## 12. st.code() Over st.graphviz_chart() for Tree Visualizations

**Problem**: A Graphviz DOT decision tree rendered via `st.graphviz_chart()` became unreadable when the graph had 10+ nodes. The chart scales the entire SVG to fit the container width, making node labels tiny.

**Root Cause**: `st.graphviz_chart(use_container_width=True)` renders as a fixed-height SVG. Horizontal graphs spread nodes wide; vertical graphs grow tall. Either way, with many leaf nodes the labels shrink below readable size. The fullscreen button helps but is bad demo UX.

**Fix**: Replace with a plain-text tree using box-drawing characters, rendered in `st.code(text, language=None)`:

```
🔷 User Query
│
├── 📋 Parse → DataDog, Dynatrace  ·  Tickers: DDOG, DT
│
├── 📊 Number Cruncher — 3 tool calls
│   ├── 🔧 Company Comparison  (tickers=DDOG, DT)
│   └── 🔧 Historical Revenue  (ticker=DDOG)
│
└── 📝 Verdict → Final Report
```

**Lesson**: For demo UIs, simple text with good formatting beats fancy graph visualizations. `st.code()` preserves monospace alignment, supports emojis, and scales naturally. Save Graphviz for offline/exported diagrams where the viewer can zoom.

---

## 13. asyncio.gather with return_exceptions for Partial Failures

**Problem**: When running financial and competitor agents in parallel via `asyncio.gather()`, if one agent threw an exception the entire gather call failed — killing the other agent's results too.

**Fix**: Use `return_exceptions=True` so exceptions are returned as values instead of raised, then check each result:

```python
financial_results, competitor_results = await asyncio.wait_for(
    asyncio.gather(
        financial_task, competitor_task,
        return_exceptions=True,  # Don't let one failure kill both
    ),
    timeout=120,
)

# Check for individual agent failures
if isinstance(financial_results, BaseException):
    financial_results = {"error": str(financial_results), "response": ""}
if isinstance(competitor_results, BaseException):
    competitor_results = {"error": str(competitor_results), "response": ""}
```

**Key Detail**: `return_exceptions=True` returns the exception object (not raises it). Check with `isinstance(result, BaseException)` — NOT `isinstance(result, Exception)` since `asyncio.CancelledError` inherits from `BaseException`.

**Also**: Wrap gather in `asyncio.wait_for(timeout=N)` to prevent agents from hanging forever. Catch `asyncio.TimeoutError` at the outer level.

---

## 14. Mocking LangGraph Agents for Testing Without API Keys

**Problem**: LangGraph agents require a real LLM (Anthropic API key) to create and run. Tests can't make real API calls in CI.

**Fix**: Mock at two levels:

1. **Agent creation level** — Patch `get_financial_agent()` to return a mock agent with an `ainvoke` AsyncMock:
```python
mock_agent = MagicMock()
final_msg = MagicMock(content="result", tool_calls=[])
mock_agent.ainvoke = AsyncMock(return_value={"messages": [final_msg], "tickers": ["DDOG"]})

with patch("src.agents.financial.get_financial_agent", return_value=mock_agent):
    result = await run_financial_agent("task", ["DDOG"])
```

2. **Sub-agent level (for manager tests)** — Patch `run_financial_agent` and `run_competitor_agent` directly:
```python
with patch("src.agents.manager.run_financial_agent", new_callable=AsyncMock, return_value=sample_response):
    result = await run_manager_agent("query")
```

**Critical**: Reset module-level singletons (`_financial_agent = None`, etc.) between tests with an autouse fixture, otherwise the first test's agent leaks into subsequent tests.

---

## 15. Singleton Reset Pattern for Test Isolation

**Problem**: LangGraph agents are created lazily and cached in module-level variables (`_financial_agent`, `_manager_agent`, etc.). Once created in one test, the same (potentially misconfigured) agent leaks into every subsequent test.

**Fix**: Autouse fixture that resets all singletons before each test:

```python
@pytest.fixture(autouse=True)
def reset_singletons():
    import src.agents.financial as fin_mod
    import src.agents.competitor as comp_mod
    import src.agents.manager as mgr_mod
    import src.tools.tavily_tools as tavily_mod

    fin_mod._financial_agent = None
    comp_mod._competitor_agent = None
    mgr_mod._manager_agent = None
    tavily_mod._tavily_client = None
    yield
```

**Lesson**: Any module-level cache/singleton is a test isolation hazard. Always provide a reset mechanism.

---

## 16. structlog for Multi-Agent Structured Logging

**Problem**: Print-statement debugging doesn't scale when you have 3+ agents running concurrently with tool calls, LLM invocations, and callbacks all interleaved.

**Fix**: Use `structlog` with JSON output — every log line includes the module name and structured key-value pairs:

```python
# src/logging_config.py
import structlog

def configure_logging(log_level="INFO"):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

# In each module:
logger = get_logger(__name__)
logger.info("financial_agent.run.start", task=task, tickers=tickers)
```

**Key Design**: Use dotted event names (`agent.stage.status`) for easy filtering: `grep "manager.execute"` shows all orchestration events.

---

## 17. Graceful Degradation in Report Generator

**Problem**: If the LLM synthesis call fails during report generation, the entire pipeline crashes — losing all the financial and competitor data that was already fetched.

**Fix**: Wrap the LLM call and fall back to basic (template-based) report generation:

```python
def _generate_with_llm(query, companies, financial_response, competitor_response, llm):
    try:
        response = llm.invoke([{"role": "user", "content": synthesis_prompt}])
        return response.content
    except Exception as e:
        logger.warning("report.llm_synthesis.error", error=str(e))
        return _generate_basic_report(query, companies, financial_response, competitor_response)
```

**Lesson**: In multi-stage pipelines, each stage should degrade gracefully rather than crash. The user gets a less polished report, but still gets the data.

---

## 18. ruff as Single Lint + Format Tool

**Problem**: Previously no linting — import sorting was inconsistent, unused imports accumulated, and formatting varied.

**Fix**: Add ruff to `pyproject.toml` with minimal config:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]  # errors, pyflakes, isort, warnings

[tool.ruff.lint.per-file-ignores]
"src/prompts/*.py" = ["E501"]  # Long lines OK in prompt templates
```

**Key Workflow**: `ruff check --fix` auto-fixes 90% of issues (import sorting, unused imports). `ruff format` handles the rest. Run both in CI as a fast-fail gate before tests.

**Gotcha**: Multiline string literals (like prompt templates) can't be reformatted without breaking the content. Use per-file-ignores for E501 on those files.
