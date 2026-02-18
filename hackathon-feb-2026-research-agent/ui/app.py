"""Streamlit UI for Research Agent Team."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import asyncio
import time
import threading
import traceback
from src.config import get_config
from src.agents.manager import run_manager_agent


# Page config
st.set_page_config(
    page_title="Rivalry Rumble-o-Tron",
    page_icon="🥊",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }
    .research-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Pipeline stage definitions
PIPELINE_STAGES = [
    {"key": "parse", "label": "Reading the matchup card", "icon_pending": "⬜", "icon_running": "🔄", "icon_done": "✅"},
    {"key": "financial", "label": "Number Cruncher", "icon_pending": "⬜", "icon_running": "📊", "icon_done": "✅"},
    {"key": "competitor", "label": "Street Scout", "icon_pending": "⬜", "icon_running": "🔍", "icon_done": "✅"},
    {"key": "synthesize", "label": "Writing the verdict", "icon_pending": "⬜", "icon_running": "📝", "icon_done": "✅"},
]

STAGE_PROGRESS = {"parse": 0.15, "financial": 0.50, "competitor": 0.50, "synthesize": 0.85}

# Funky status quips shown while each stage is running (cycled by poll tick)
STAGE_QUIPS = {
    "parse": [
        "Sizing up the contenders...",
        "Reading the tale of the tape...",
    ],
    "financial": [
        "Munching on earnings reports...",
        "Digging through balance sheets...",
        "Crunching the hard numbers...",
    ],
    "competitor": [
        "Scouting the competition...",
        "Reading the industry gossip...",
        "Gathering street intel...",
    ],
    "synthesize": [
        "Brewing the final verdict...",
        "Polishing the championship belt...",
        "Writing up the scorecards...",
    ],
}


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False


def validate_config():
    """Validate API configuration."""
    config = get_config()
    errors = config.validate()

    if errors:
        st.error("⚠️ Configuration Required")
        st.markdown("""
        Please set the following environment variables in your `.env` file:

        ```bash
        ANTHROPIC_API_KEY=your_key_here
        TAVILY_API_KEY=your_key_here
        ```

        Missing:
        """ + "\n".join(f"- {e}" for e in errors))
        return False

    return True


def display_header():
    """Display the app header."""
    st.title("🥊 Rivalry Rumble-o-Tron")
    st.markdown("*Drop a company matchup. We'll dig up the financials, scout the competition, and deliver the verdict.*")


EXAMPLE_QUERIES = [
    {
        "title": "📊 Observability Showdown",
        "desc": "Cisco (Splunk + AppDynamics) vs DataDog vs Dynatrace — who owns the observability ring?",
        "query": "Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace",
    },
    {
        "title": "📈 DataDog vs Dynatrace",
        "desc": "A head-to-head on financials, growth, and competitive positioning.",
        "query": "Analyze DataDog vs Dynatrace - financial performance and competitive positioning",
    },
    {
        "title": "☁️ Cloud Wars",
        "desc": "AWS vs Azure vs GCP — market share, revenue, and strategic bets compared.",
        "query": "Compare AWS, Microsoft Azure, and Google Cloud Platform - market share, revenue growth, and competitive strategy",
    },
]


def display_example_queries():
    """Display example queries as styled cards."""
    st.markdown("### 💡 Try a Matchup")

    cols = st.columns(len(EXAMPLE_QUERIES))

    for i, ex in enumerate(EXAMPLE_QUERIES):
        with cols[i]:
            st.markdown(f"**{ex['title']}**")
            st.caption(ex["desc"])
            if st.button("Run this", key=f"example_{i}", use_container_width=True):
                return ex["query"]

    return None


def display_chat_history():
    """Display chat message history with optional agent activity log."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Render agent activity log if metadata is present
            meta = message.get("metadata")
            if meta and message["role"] == "assistant":
                with st.expander("🔎 Behind the Scenes"):
                    companies = meta.get("companies", [])
                    tickers = meta.get("tickers", [])
                    elapsed = meta.get("elapsed", 0)
                    fin = meta.get("financial_results") or {}
                    comp = meta.get("competitor_results") or {}

                    st.markdown(f"**Companies identified:** {', '.join(companies)}")
                    st.markdown(f"**Tickers analyzed:** {', '.join(tickers)}")
                    st.markdown(f"**Completed in:** {int(elapsed)}s")
                    st.divider()

                    col_fin, col_comp = st.columns(2)
                    with col_fin:
                        st.markdown("**📊 Number Cruncher**")
                        st.caption(f"LLM round-trips: {fin.get('message_count', '?')}")
                        if fin.get("tickers"):
                            st.caption(f"Tickers: {', '.join(fin['tickers'])}")

                    with col_comp:
                        st.markdown("**🔍 Street Scout**")
                        st.caption(f"LLM round-trips: {comp.get('message_count', '?')}")
                        if comp.get("companies"):
                            st.caption(f"Companies: {', '.join(comp['companies'])}")


def render_stage_text(stage_states: dict, tick: int = 0) -> str:
    """Render stage status as markdown text with funky quips."""
    lines = []
    for stage_def in PIPELINE_STAGES:
        key = stage_def["key"]
        state = stage_states.get(key, {"status": "pending", "detail": ""})
        status = state["status"]

        if status == "done":
            icon = stage_def["icon_done"]
            detail_str = ""
        elif status == "running":
            icon = stage_def["icon_running"]
            quips = STAGE_QUIPS.get(key, [])
            quip = quips[tick % len(quips)] if quips else ""
            detail_str = f" — *{quip}*" if quip else ""
        else:
            icon = stage_def["icon_pending"]
            detail_str = ""

        lines.append(f"{icon} **{stage_def['label']}**{detail_str}")

    return "\n\n".join(lines)


def compute_progress(stage_states: dict) -> float:
    """Compute progress bar value from stage states."""
    done_stages = [k for k, v in stage_states.items() if v.get("status") == "done"]
    running_stages = [k for k, v in stage_states.items() if v.get("status") == "running"]

    progress = 0.0
    for s in done_stages:
        progress = max(progress, STAGE_PROGRESS.get(s, 0) + 0.10)
    for s in running_stages:
        progress = max(progress, STAGE_PROGRESS.get(s, 0))

    return min(progress, 0.95)


def process_query(query: str):
    """Process a research query with progress indicators."""
    st.session_state.is_processing = True

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("assistant"):
        progress_bar = st.progress(0.0)
        stages_placeholder = st.empty()
        elapsed_placeholder = st.empty()
        result_placeholder = st.empty()

        # Shared mutable state between main thread and worker thread
        stage_states = {}
        start_time = time.time()
        worker_result = [None]  # [0] = report string
        worker_error = [None]   # [0] = exception

        # Initial render
        stages_placeholder.markdown(render_stage_text(stage_states))
        elapsed_placeholder.caption("0s elapsed")

        def progress_callback(update):
            """Handle structured progress updates — only mutates shared dict.

            This runs in the worker thread, so it must NOT call Streamlit APIs.
            """
            if isinstance(update, dict):
                stage = update.get("stage")
                if stage:
                    stage_states[stage] = {
                        "status": update.get("status", "running"),
                        "detail": update.get("detail", ""),
                    }

        def _run_agent():
            """Worker thread: runs the async agent in its own event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                worker_result[0] = loop.run_until_complete(
                    run_manager_agent(query, progress_callback)
                )
            except Exception as e:
                worker_error[0] = e
            finally:
                loop.close()

        try:
            # Start the agent in a background thread
            thread = threading.Thread(target=_run_agent, daemon=True)
            thread.start()

            # Poll the thread, updating Streamlit UI from the main thread
            tick = 0
            while thread.is_alive():
                thread.join(timeout=1.5)
                tick += 1

                # Update UI from main thread (safe for Streamlit)
                stages_placeholder.markdown(render_stage_text(stage_states, tick))
                progress_bar.progress(compute_progress(stage_states))
                elapsed = time.time() - start_time
                elapsed_placeholder.caption(f"{int(elapsed)}s elapsed")

            # Thread finished — check for errors
            if worker_error[0]:
                raise worker_error[0]

            agent_output = worker_result[0]
            report = agent_output["final_report"]

            # Show completion
            progress_bar.progress(1.0)
            elapsed = time.time() - start_time
            elapsed_placeholder.caption(f"Completed in {int(elapsed)}s")

            # Mark all stages done
            for stage_def in PIPELINE_STAGES:
                stage_states[stage_def["key"]] = {"status": "done", "detail": ""}
            stages_placeholder.markdown(render_stage_text(stage_states))

            # Brief pause so user sees 100%, then collapse progress and show report
            time.sleep(0.5)
            progress_bar.empty()
            stages_placeholder.empty()
            elapsed_placeholder.empty()
            result_placeholder.markdown(report)

            # Store metadata for "Behind the Scenes" expander (survives rerun)
            fin = agent_output.get("financial_results") or {}
            comp = agent_output.get("competitor_results") or {}
            # Strip the large response text to keep session state lean
            metadata = {
                "companies": agent_output.get("companies", []),
                "tickers": agent_output.get("tickers", []),
                "elapsed": elapsed,
                "financial_results": {
                    "message_count": fin.get("message_count"),
                    "tickers": fin.get("tickers"),
                },
                "competitor_results": {
                    "message_count": comp.get("message_count"),
                    "companies": comp.get("companies"),
                },
            }

            # Add to message history
            st.session_state.messages.append({
                "role": "assistant",
                "content": report,
                "metadata": metadata,
            })

        except Exception as e:
            progress_bar.empty()
            stages_placeholder.empty()
            elapsed_placeholder.empty()
            tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
            print(f"ERROR in process_query:\n{''.join(tb_lines)}", flush=True)
            error_msg = f"❌ Error: {type(e).__name__}: {str(e) or 'See server logs'}"
            result_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.session_state.is_processing = False


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    display_header()

    # Validate configuration
    if not validate_config():
        return

    st.divider()

    # Example queries
    example_query = display_example_queries()

    st.divider()

    # Chat history
    st.markdown("### 🥊 The Ring")
    display_chat_history()

    # Chat input
    if prompt := st.chat_input("Who's going head-to-head? Drop your matchup here...", disabled=st.session_state.is_processing):
        process_query(prompt)
        st.rerun()

    # Handle example query click
    if example_query:
        process_query(example_query)
        st.rerun()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888;">
    Rivalry Rumble-o-Tron v0.1 | Built with LangGraph + Claude + Streamlit
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
