"""Competitor Agent - analyzes competitive positioning using Tavily search."""

from typing import Any, Annotated, TypedDict
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..config import get_config
from ..prompts.competitor_prompt import COMPETITOR_SYSTEM_PROMPT
from ..tools.tavily_tools import (
    search_company_info,
    search_competitive_analysis,
    search_product_info,
    search_market_trends,
)


class CompetitorState(TypedDict):
    """State for competitor agent."""
    messages: Annotated[list, add_messages]
    companies: list[str]


# Tools available to the competitor agent
COMPETITOR_TOOLS = [
    search_company_info,
    search_competitive_analysis,
    search_product_info,
    search_market_trends,
]


def _extract_tool_calls(messages: list) -> list[dict]:
    """Extract tool call details from LangGraph message history."""
    tool_calls = []
    pending = {}
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = {
                    "tool": tc["name"],
                    "args": tc["args"],
                }
        if msg.__class__.__name__ == "ToolMessage":
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and call_id in pending:
                info = pending.pop(call_id)
                content = msg.content if hasattr(msg, "content") else str(msg)
                if isinstance(content, str) and len(content) > 200:
                    content = content[:200] + "..."
                tool_calls.append({
                    "tool": info["tool"],
                    "args": info["args"],
                    "result_preview": content,
                })
    return tool_calls


def create_competitor_agent():
    """Create the competitor analysis agent."""
    config = get_config()

    # Initialize the LLM with tools
    llm = ChatAnthropic(
        model=config.model_name,
        temperature=config.model_temperature,
        api_key=config.anthropic_api_key,
    )
    llm_with_tools = llm.bind_tools(COMPETITOR_TOOLS)

    # Create tool node
    tool_node = ToolNode(COMPETITOR_TOOLS)

    def should_continue(state: CompetitorState) -> str:
        """Determine if agent should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If LLM makes a tool call, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Otherwise, end
        return END

    def call_model(state: CompetitorState) -> dict:
        """Call the LLM."""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(CompetitorState)

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
_competitor_agent = None


def get_competitor_agent():
    """Get or create the competitor agent instance."""
    global _competitor_agent
    if _competitor_agent is None:
        _competitor_agent = create_competitor_agent()
    return _competitor_agent


async def run_competitor_agent(task: str, companies: list[str] | None = None) -> dict[str, Any]:
    """
    Run the competitor agent to analyze companies.

    Args:
        task: Description of the competitive analysis task
        companies: Optional list of company names to analyze

    Returns:
        Dictionary containing competitive analysis results.
    """
    agent = get_competitor_agent()

    # Build the prompt
    if companies:
        company_info = f"\n\nAnalyze the following companies: {', '.join(companies)}"
    else:
        company_info = ""

    messages = [
        SystemMessage(content=COMPETITOR_SYSTEM_PROMPT),
        HumanMessage(content=f"{task}{company_info}"),
    ]

    # Run the agent
    result = await agent.ainvoke({
        "messages": messages,
        "companies": companies or [],
    })

    # Extract the final response
    final_message = result["messages"][-1]

    # Extract tool call log from message history
    tool_calls = _extract_tool_calls(result["messages"])

    return {
        "task": task,
        "companies": companies,
        "response": final_message.content if hasattr(final_message, "content") else str(final_message),
        "message_count": len(result["messages"]),
        "tool_calls": tool_calls,
    }


def run_competitor_agent_sync(task: str, companies: list[str] | None = None) -> dict[str, Any]:
    """Synchronous wrapper for run_competitor_agent."""
    import asyncio
    return asyncio.run(run_competitor_agent(task, companies))
