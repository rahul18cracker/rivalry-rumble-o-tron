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
    {"key": "parse", "label": "Analyzing Query", "icon_pending": "⬜", "icon_running": "🔄", "icon_done": "✅"},
    {"key": "financial", "label": "Financial Agent", "icon_pending": "⬜", "icon_running": "📊", "icon_done": "✅"},
    {"key": "competitor", "label": "Competitor Agent", "icon_pending": "⬜", "icon_running": "🔍", "icon_done": "✅"},
    {"key": "synthesize", "label": "Synthesizing Report", "icon_pending": "⬜", "icon_running": "📝", "icon_done": "✅"},
]

STAGE_PROGRESS = {"parse": 0.15, "financial": 0.50, "competitor": 0.50, "synthesize": 0.85}


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


def display_example_queries():
    """Display example queries as clickable buttons."""
    st.markdown("### 💡 Example Queries")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Observability Market Analysis", use_container_width=True):
            return "Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace"

    with col2:
        if st.button("📈 DataDog vs Dynatrace", use_container_width=True):
            return "Analyze DataDog vs Dynatrace - financial performance and competitive positioning"

    return None


def display_chat_history():
    """Display chat message history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def render_stage_text(stage_states: dict) -> str:
    """Render stage status as markdown text."""
    lines = []
    for stage_def in PIPELINE_STAGES:
        key = stage_def["key"]
        state = stage_states.get(key, {"status": "pending", "detail": ""})
        status = state["status"]
        detail = state.get("detail", "")

        if status == "done":
            icon = stage_def["icon_done"]
        elif status == "running":
            icon = stage_def["icon_running"]
        else:
            icon = stage_def["icon_pending"]

        detail_str = f" — {detail}" if detail else ""
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
            while thread.is_alive():
                thread.join(timeout=1.0)

                # Update UI from main thread (safe for Streamlit)
                stages_placeholder.markdown(render_stage_text(stage_states))
                progress_bar.progress(compute_progress(stage_states))
                elapsed = time.time() - start_time
                elapsed_placeholder.caption(f"{int(elapsed)}s elapsed")

            # Thread finished — check for errors
            if worker_error[0]:
                raise worker_error[0]

            report = worker_result[0]

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

            # Add to message history
            st.session_state.messages.append({"role": "assistant", "content": report})

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
