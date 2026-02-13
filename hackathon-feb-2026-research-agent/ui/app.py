"""Streamlit UI for Research Agent Team."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import asyncio
from src.config import get_config
from src.agents.manager import run_manager_agent


# Page config
st.set_page_config(
    page_title="Research Agent Team",
    page_icon="🔍",
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


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_status" not in st.session_state:
        st.session_state.current_status = ""
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
    st.title("🔍 Research Agent Team")
    st.markdown("""
    Multi-agent research system for competitive analysis.

    **How it works:**
    1. Enter your research query
    2. The Manager Agent delegates to specialized sub-agents
    3. Financial Agent analyzes market data
    4. Competitor Agent researches positioning
    5. Results are synthesized into a comprehensive report
    """)


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


def update_status(status: str):
    """Update the status display."""
    st.session_state.current_status = status


async def process_query(query: str):
    """Process a research query."""
    st.session_state.is_processing = True

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": query})

    # Create a placeholder for the assistant response
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        result_placeholder = st.empty()

        # Show progress
        status_placeholder.markdown("🔄 **Starting research...**")

        try:
            # Define progress callback
            def progress_callback(status: str):
                status_placeholder.markdown(f"🔄 **{status}**")

            # Run the manager agent
            report = await run_manager_agent(query, progress_callback)

            # Clear status and show results
            status_placeholder.empty()
            result_placeholder.markdown(report)

            # Add to message history
            st.session_state.messages.append({"role": "assistant", "content": report})

        except Exception as e:
            status_placeholder.empty()
            error_msg = f"❌ Error: {str(e)}"
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
    st.markdown("### 💬 Research Chat")
    display_chat_history()

    # Chat input
    if prompt := st.chat_input("Enter your research query...", disabled=st.session_state.is_processing):
        asyncio.run(process_query(prompt))
        st.rerun()

    # Handle example query click
    if example_query:
        asyncio.run(process_query(example_query))
        st.rerun()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888;">
    Research Agent Team v0.1 | Built with LangGraph + Claude + Streamlit
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
