"""Manager Agent - orchestrates research by delegating to sub-agents."""

import asyncio
import json
from typing import Any, TypedDict, Literal
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END

from ..config import get_config
from ..prompts.manager_prompt import MANAGER_SYSTEM_PROMPT
from .financial import run_financial_agent
from .competitor import run_competitor_agent
from ..report.generator import generate_report


class ResearchTask(TypedDict):
    """A single research task."""
    agent: Literal["financial", "competitor"]
    task: str
    companies: list[str]
    tickers: list[str]


class ManagerState(TypedDict):
    """State for manager agent."""
    messages: list
    user_query: str
    companies: list[str]
    tickers: list[str]
    tasks: list[ResearchTask]
    financial_results: dict | None
    competitor_results: dict | None
    final_report: str
    status: str
    progress_callback: Any | None


def create_manager_agent():
    """Create the manager orchestration agent."""
    config = get_config()

    # Initialize the LLM
    llm = ChatAnthropic(
        model=config.model_name,
        temperature=config.model_temperature,
        api_key=config.anthropic_api_key,
    )

    def parse_request(state: ManagerState) -> dict:
        """Parse the user request to identify companies and create task plan."""
        user_query = state["user_query"]
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "parse", "status": "running", "detail": "Analyzing query..."})

        # Use LLM to parse the request
        parse_prompt = f"""Analyze this research request and extract:
1. Companies to analyze
2. Stock tickers (CSCO for Cisco/Splunk/AppDynamics, DDOG for DataDog, DT for Dynatrace)
3. Research focus areas

Request: {user_query}

Respond with JSON only:
{{
    "companies": ["Company1", "Company2"],
    "tickers": ["TICK1", "TICK2"],
    "focus": "Brief description of research focus"
}}"""

        response = llm.invoke([{"role": "user", "content": parse_prompt}])

        try:
            # Try to parse JSON from response
            content = response.content
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())
            companies = parsed.get("companies", [])
            tickers = parsed.get("tickers", [])
        except (json.JSONDecodeError, IndexError):
            # Fallback to default companies for observability analysis
            companies = ["Cisco (Splunk/AppDynamics)", "DataDog", "Dynatrace"]
            tickers = ["CSCO", "DDOG", "DT"]

        # Create tasks for sub-agents
        tasks = [
            {
                "agent": "financial",
                "task": f"Analyze financial metrics for: {', '.join(companies)}",
                "companies": companies,
                "tickers": tickers,
            },
            {
                "agent": "competitor",
                "task": f"Analyze competitive positioning for: {', '.join(companies)}",
                "companies": companies,
                "tickers": tickers,
            },
        ]

        if callback:
            callback({"stage": "parse", "status": "done", "detail": f"Found {len(companies)} companies"})

        return {
            "companies": companies,
            "tickers": tickers,
            "tasks": tasks,
            "status": "tasks_created",
        }

    async def execute_tasks(state: ManagerState) -> dict:
        """Execute sub-agent tasks in parallel."""
        tasks = state["tasks"]
        tickers = state["tickers"]
        companies = state["companies"]
        callback = state.get("progress_callback")

        # Update progress
        if callback:
            callback({"stage": "financial", "status": "running", "detail": "Fetching market data..."})
            callback({"stage": "competitor", "status": "pending", "detail": "Waiting..."})

        # Run both agents in parallel
        financial_task = None
        competitor_task = None

        for task in tasks:
            if task["agent"] == "financial":
                financial_task = run_financial_agent(task["task"], tickers)
            elif task["agent"] == "competitor":
                competitor_task = run_competitor_agent(task["task"], companies)

        # Start both concurrently
        if callback:
            callback({"stage": "competitor", "status": "running", "detail": "Searching competitive landscape..."})

        async def _noop():
            return None

        financial_results, competitor_results = await asyncio.gather(
            financial_task if financial_task else _noop(),
            competitor_task if competitor_task else _noop(),
        )

        if callback:
            callback({"stage": "financial", "status": "done", "detail": "Financial analysis complete"})
            callback({"stage": "competitor", "status": "done", "detail": "Competitor research complete"})

        return {
            "financial_results": financial_results,
            "competitor_results": competitor_results,
            "status": "tasks_completed",
        }

    def synthesize_report(state: ManagerState) -> dict:
        """Synthesize final report from agent outputs."""
        user_query = state["user_query"]
        companies = state["companies"]
        financial_results = state["financial_results"]
        competitor_results = state["competitor_results"]
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "synthesize", "status": "running", "detail": "Writing final report..."})

        # Generate the report
        report = generate_report(
            query=user_query,
            companies=companies,
            financial_data=financial_results,
            competitor_data=competitor_results,
            llm=llm,
        )

        if callback:
            callback({"stage": "synthesize", "status": "done", "detail": "Report ready"})

        return {
            "final_report": report,
            "status": "completed",
        }

    # Build the graph
    workflow = StateGraph(ManagerState)

    # Add nodes
    workflow.add_node("parse", parse_request)
    workflow.add_node("execute", execute_tasks)
    workflow.add_node("synthesize", synthesize_report)

    # Set entry point
    workflow.set_entry_point("parse")

    # Add edges
    workflow.add_edge("parse", "execute")
    workflow.add_edge("execute", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile()


# Create the agent instance
_manager_agent = None


def get_manager_agent():
    """Get or create the manager agent instance."""
    global _manager_agent
    if _manager_agent is None:
        _manager_agent = create_manager_agent()
    return _manager_agent


async def run_manager_agent(
    query: str,
    progress_callback: Any | None = None,
) -> str:
    """
    Run the manager agent to orchestrate research.

    Args:
        query: User's research query
        progress_callback: Optional callback function for progress updates

    Returns:
        The final research report as markdown.
    """
    agent = get_manager_agent()

    # Initialize state
    initial_state = {
        "messages": [],
        "user_query": query,
        "companies": [],
        "tickers": [],
        "tasks": [],
        "financial_results": None,
        "competitor_results": None,
        "final_report": "",
        "status": "started",
        "progress_callback": progress_callback,
    }

    # Run the agent
    result = await agent.ainvoke(initial_state)

    return result["final_report"]


def run_manager_agent_sync(
    query: str,
    progress_callback: Any | None = None,
) -> str:
    """Synchronous wrapper for run_manager_agent."""
    return asyncio.run(run_manager_agent(query, progress_callback))
