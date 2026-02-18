"""Financial Agent - analyzes company financial data using yfinance."""

from typing import Any, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..config import get_config
from ..prompts.financial_prompt import FINANCIAL_SYSTEM_PROMPT
from ..tools.yfinance_tools import (
    get_company_financials,
    get_historical_revenue,
    get_company_comparison,
)


from typing import TypedDict

class FinancialState(TypedDict):
    """State for financial agent."""
    messages: Annotated[list, add_messages]
    tickers: list[str]


# Tools available to the financial agent
FINANCIAL_TOOLS = [
    get_company_financials,
    get_historical_revenue,
    get_company_comparison,
]


def _extract_tool_calls(messages: list) -> list[dict]:
    """Extract tool call details from LangGraph message history."""
    tool_calls = []
    # Build a map of tool_call_id → tool call info from AIMessages
    pending = {}
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = {
                    "tool": tc["name"],
                    "args": tc["args"],
                }
        # Match ToolMessage responses back to their calls
        if msg.__class__.__name__ == "ToolMessage":
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and call_id in pending:
                info = pending.pop(call_id)
                # Summarise the result to keep metadata lean
                content = msg.content if hasattr(msg, "content") else str(msg)
                if isinstance(content, str) and len(content) > 200:
                    content = content[:200] + "..."
                tool_calls.append({
                    "tool": info["tool"],
                    "args": info["args"],
                    "result_preview": content,
                })
    return tool_calls


def create_financial_agent():
    """Create the financial analysis agent."""
    config = get_config()

    # Initialize the LLM with tools
    llm = ChatAnthropic(
        model=config.model_name,
        temperature=config.model_temperature,
        api_key=config.anthropic_api_key,
    )
    llm_with_tools = llm.bind_tools(FINANCIAL_TOOLS)

    # Create tool node
    tool_node = ToolNode(FINANCIAL_TOOLS)

    def should_continue(state: FinancialState) -> str:
        """Determine if agent should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If LLM makes a tool call, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Otherwise, end
        return END

    def call_model(state: FinancialState) -> dict:
        """Call the LLM."""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(FinancialState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# Create the agent instance
_financial_agent = None


def get_financial_agent():
    """Get or create the financial agent instance."""
    global _financial_agent
    if _financial_agent is None:
        _financial_agent = create_financial_agent()
    return _financial_agent


async def run_financial_agent(task: str, tickers: list[str] | None = None) -> dict[str, Any]:
    """
    Run the financial agent to analyze companies.

    Args:
        task: Description of the financial analysis task
        tickers: Optional list of stock tickers to analyze

    Returns:
        Dictionary containing financial analysis results.
    """
    agent = get_financial_agent()

    # Build the prompt
    if tickers:
        ticker_info = f"\n\nAnalyze the following tickers: {', '.join(tickers)}"
    else:
        ticker_info = ""

    messages = [
        SystemMessage(content=FINANCIAL_SYSTEM_PROMPT),
        HumanMessage(content=f"{task}{ticker_info}"),
    ]

    # Run the agent
    result = await agent.ainvoke({
        "messages": messages,
        "tickers": tickers or [],
    })

    # Extract the final response
    final_message = result["messages"][-1]

    # Extract tool call log from message history
    tool_calls = _extract_tool_calls(result["messages"])

    return {
        "task": task,
        "tickers": tickers,
        "response": final_message.content if hasattr(final_message, "content") else str(final_message),
        "message_count": len(result["messages"]),
        "tool_calls": tool_calls,
    }


def run_financial_agent_sync(task: str, tickers: list[str] | None = None) -> dict[str, Any]:
    """Synchronous wrapper for run_financial_agent."""
    import asyncio
    return asyncio.run(run_financial_agent(task, tickers))
