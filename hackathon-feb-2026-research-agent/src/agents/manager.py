"""Manager Agent - orchestrates research by delegating to sub-agents."""

import asyncio
import json
from typing import Any, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph

from ..config import get_config
from ..logging_config import get_logger
from ..report.generator import generate_report
from .competitor import run_competitor_agent
from .financial import run_financial_agent
from .followup import build_focused_task, route_query, synthesize_followup
from .market_intel import run_market_intel_agent

logger = get_logger(__name__)


class ResearchTask(TypedDict):
    """A single research task."""

    agent: Literal["financial", "competitor", "market_intel"]
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
    market_intel_results: dict | None
    final_report: str
    status: str
    progress_callback: Any | None
    # Follow-up context fields
    prior_report: str | None
    prior_results: dict | None
    query_type: str
    followup_agents: list[str]
    focused_task: str


def create_manager_agent():
    """Create the manager orchestration agent."""
    config = get_config()

    # Initialize the LLM
    llm = ChatAnthropic(
        model=config.model_name,
        temperature=config.model_temperature,
        api_key=config.anthropic_api_key,
    )

    def route_request(state: ManagerState) -> dict:
        """Classify query and determine execution path."""
        prior_report = state.get("prior_report")
        user_query = state["user_query"]
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "route", "status": "running", "detail": "Classifying query..."})

        logger.info("manager.route.start", query=user_query, has_prior=bool(prior_report))

        classification = route_query(user_query, prior_report, llm)

        query_type = classification["query_type"]
        agents_needed = classification["agents_needed"]
        focused_task = classification["focused_task"]

        logger.info(
            "manager.route.end",
            query_type=query_type,
            agents_needed=agents_needed,
        )
        if callback:
            callback(
                {
                    "stage": "route",
                    "status": "done",
                    "detail": f"Query type: {query_type}",
                    "query_type": query_type,
                    "followup_agents": agents_needed,
                }
            )

        return {
            "query_type": query_type,
            "followup_agents": agents_needed,
            "focused_task": focused_task,
        }

    def parse_request(state: ManagerState) -> dict:
        """Parse the user request to identify companies and create task plan."""
        user_query = state["user_query"]
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "parse", "status": "running", "detail": "Analyzing query..."})

        logger.info("manager.parse.start", query=user_query)

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

        try:
            response = llm.invoke([{"role": "user", "content": parse_prompt}])

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
            logger.warning("manager.parse.json_error", query=user_query)
            companies = ["Cisco (Splunk/AppDynamics)", "DataDog", "Dynatrace"]
            tickers = ["CSCO", "DDOG", "DT"]
        except Exception as e:
            logger.error("manager.parse.llm_error", error=str(e))
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
            {
                "agent": "market_intel",
                "task": f"Analyze market intelligence and trends for: {', '.join(companies)}",
                "companies": companies,
                "tickers": tickers,
            },
        ]

        logger.info("manager.parse.end", companies=companies, tickers=tickers)
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
            callback({"stage": "market_intel", "status": "pending", "detail": "Waiting..."})

        logger.info("manager.execute.start", company_count=len(companies))

        # Run all agents in parallel
        financial_task = None
        competitor_task = None
        market_intel_task = None

        for task in tasks:
            if task["agent"] == "financial":
                financial_task = run_financial_agent(task["task"], tickers)
            elif task["agent"] == "competitor":
                competitor_task = run_competitor_agent(task["task"], companies)
            elif task["agent"] == "market_intel":
                market_intel_task = run_market_intel_agent(task["task"], companies)

        # Start all concurrently
        if callback:
            callback({"stage": "competitor", "status": "running", "detail": "Searching competitive landscape..."})
            callback({"stage": "market_intel", "status": "running", "detail": "Scanning market trends..."})

        async def _noop():
            return None

        try:
            financial_results, competitor_results, market_intel_results = await asyncio.wait_for(
                asyncio.gather(
                    financial_task if financial_task else _noop(),
                    competitor_task if competitor_task else _noop(),
                    market_intel_task if market_intel_task else _noop(),
                    return_exceptions=True,
                ),
                timeout=300,
            )
        except asyncio.TimeoutError:
            logger.error("manager.execute.timeout")
            financial_results = {"error": "Timeout", "response": ""}
            competitor_results = {"error": "Timeout", "response": ""}
            market_intel_results = {"error": "Timeout", "response": ""}

        # Handle individual agent exceptions returned by gather(return_exceptions=True)
        if isinstance(financial_results, BaseException):
            logger.error("manager.execute.financial_error", error=str(financial_results))
            financial_results = {"error": str(financial_results), "response": ""}
        if isinstance(competitor_results, BaseException):
            logger.error("manager.execute.competitor_error", error=str(competitor_results))
            competitor_results = {"error": str(competitor_results), "response": ""}
        if isinstance(market_intel_results, BaseException):
            logger.error("manager.execute.market_intel_error", error=str(market_intel_results))
            market_intel_results = {"error": str(market_intel_results), "response": ""}

        logger.info("manager.execute.end")
        if callback:
            callback({"stage": "financial", "status": "done", "detail": "Financial analysis complete"})
            callback({"stage": "competitor", "status": "done", "detail": "Competitor research complete"})
            callback({"stage": "market_intel", "status": "done", "detail": "Market intelligence complete"})

        return {
            "financial_results": financial_results,
            "competitor_results": competitor_results,
            "market_intel_results": market_intel_results,
            "status": "tasks_completed",
        }

    def synthesize_report(state: ManagerState) -> dict:
        """Synthesize final report from agent outputs."""
        user_query = state["user_query"]
        companies = state["companies"]
        financial_results = state["financial_results"]
        competitor_results = state["competitor_results"]
        market_intel_results = state["market_intel_results"]
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "synthesize", "status": "running", "detail": "Writing final report..."})

        logger.info("manager.synthesize.start")
        try:
            report = generate_report(
                query=user_query,
                companies=companies,
                financial_data=financial_results,
                competitor_data=competitor_results,
                market_intel_data=market_intel_results,
                llm=llm,
            )
        except Exception as e:
            logger.error("manager.synthesize.error", error=str(e))
            report = f"# Error Generating Report\n\nAn error occurred during report synthesis: {e}"

        logger.info("manager.synthesize.end")
        if callback:
            callback({"stage": "synthesize", "status": "done", "detail": "Report ready"})

        return {
            "final_report": report,
            "status": "completed",
        }

    async def execute_followup_tasks(state: ManagerState) -> dict:
        """Execute only the selected sub-agents for a follow-up question."""
        agents_needed = state.get("followup_agents", [])
        focused_task_str = state.get("focused_task", state["user_query"])
        prior_report = state.get("prior_report", "")
        prior_results = state.get("prior_results") or {}
        callback = state.get("progress_callback")

        # Use companies/tickers from prior results, or defaults
        companies = prior_results.get("companies", state.get("companies", []))
        tickers = prior_results.get("tickers", state.get("tickers", []))

        logger.info("manager.execute_followup.start", agents=agents_needed)

        async def _noop():
            return None

        coros = []
        agent_order = []

        for agent_name in agents_needed:
            task_str = build_focused_task(agent_name, focused_task_str, prior_report or "", companies)

            if agent_name == "financial":
                if callback:
                    callback({"stage": "financial", "status": "running", "detail": "Re-checking financials..."})
                coros.append(run_financial_agent(task_str, tickers))
                agent_order.append("financial")
            elif agent_name == "competitor":
                if callback:
                    callback({"stage": "competitor", "status": "running", "detail": "Digging deeper on competitors..."})
                coros.append(run_competitor_agent(task_str, companies))
                agent_order.append("competitor")
            elif agent_name == "market_intel":
                if callback:
                    callback({"stage": "market_intel", "status": "running", "detail": "Fetching market updates..."})
                coros.append(run_market_intel_agent(task_str, companies))
                agent_order.append("market_intel")

        if not coros:
            return {"status": "followup_no_agents"}

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=300,
            )
        except asyncio.TimeoutError:
            logger.error("manager.execute_followup.timeout")
            results = [{"error": "Timeout", "response": ""} for _ in coros]

        new_results = {}
        for agent_name, result in zip(agent_order, results):
            if isinstance(result, BaseException):
                logger.error(f"manager.execute_followup.{agent_name}_error", error=str(result))
                result = {"error": str(result), "response": ""}
            new_results[f"{agent_name}_results"] = result
            if callback:
                callback({"stage": agent_name, "status": "done", "detail": f"{agent_name} follow-up complete"})

        # Store companies/tickers in state for downstream use
        logger.info("manager.execute_followup.end")
        return {
            "financial_results": new_results.get("financial_results", state.get("financial_results")),
            "competitor_results": new_results.get("competitor_results", state.get("competitor_results")),
            "market_intel_results": new_results.get("market_intel_results", state.get("market_intel_results")),
            "companies": companies,
            "tickers": tickers,
            "status": "followup_tasks_completed",
        }

    def synthesize_followup_response(state: ManagerState) -> dict:
        """Generate a conversational follow-up response."""
        user_query = state["user_query"]
        prior_report = state.get("prior_report", "")
        prior_results = state.get("prior_results")
        callback = state.get("progress_callback")

        if callback:
            callback({"stage": "synthesize", "status": "running", "detail": "Composing follow-up answer..."})

        logger.info("manager.synthesize_followup.start")

        # Build new_results from state if agents were re-run
        new_results = None
        if state.get("query_type") == "followup_with_agents":
            new_results = {
                "financial_results": state.get("financial_results"),
                "competitor_results": state.get("competitor_results"),
                "market_intel_results": state.get("market_intel_results"),
            }

        response = synthesize_followup(
            query=user_query,
            prior_report=prior_report or "",
            prior_results=prior_results,
            new_results=new_results,
            llm=llm,
        )

        logger.info("manager.synthesize_followup.end")
        if callback:
            callback({"stage": "synthesize", "status": "done", "detail": "Follow-up ready"})

        # Carry forward companies/tickers from prior_results if not already set
        companies = state.get("companies", [])
        tickers = state.get("tickers", [])
        if not companies and prior_results:
            companies = prior_results.get("companies", [])
            tickers = prior_results.get("tickers", [])

        return {
            "final_report": response,
            "companies": companies,
            "tickers": tickers,
            "status": "completed",
        }

    # ---- Conditional routing ----
    def route_after_classify(state: ManagerState) -> str:
        query_type = state.get("query_type", "new_research")
        if query_type == "followup_with_agents":
            return "execute_followup"
        elif query_type == "followup_context_only":
            return "synthesize_followup"
        else:
            return "parse"

    # Build the graph
    workflow = StateGraph(ManagerState)

    # Add nodes
    workflow.add_node("route", route_request)
    workflow.add_node("parse", parse_request)
    workflow.add_node("execute", execute_tasks)
    workflow.add_node("synthesize", synthesize_report)
    workflow.add_node("execute_followup", execute_followup_tasks)
    workflow.add_node("synthesize_followup", synthesize_followup_response)

    # Set entry point
    workflow.set_entry_point("route")

    # Conditional edge from route
    workflow.add_conditional_edges(
        "route",
        route_after_classify,
        {
            "parse": "parse",
            "execute_followup": "execute_followup",
            "synthesize_followup": "synthesize_followup",
        },
    )

    # Original pipeline edges
    workflow.add_edge("parse", "execute")
    workflow.add_edge("execute", "synthesize")
    workflow.add_edge("synthesize", END)

    # Follow-up pipeline edges
    workflow.add_edge("execute_followup", "synthesize_followup")
    workflow.add_edge("synthesize_followup", END)

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
    prior_report: str | None = None,
    prior_results: dict | None = None,
) -> dict:
    """
    Run the manager agent to orchestrate research.

    Args:
        query: User's research query
        progress_callback: Optional callback function for progress updates
        prior_report: Previous report markdown (enables follow-up routing)
        prior_results: Previous agent results dict (enables context-only follow-ups)

    Returns:
        Dict with keys: final_report, companies, tickers, financial_results,
        competitor_results, market_intel_results, query_type, followup_agents.
    """
    logger.info("manager_agent.run.start", query=query, has_prior=bool(prior_report))
    try:
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
            "market_intel_results": None,
            "final_report": "",
            "status": "started",
            "progress_callback": progress_callback,
            # Follow-up context
            "prior_report": prior_report,
            "prior_results": prior_results,
            "query_type": "",
            "followup_agents": [],
            "focused_task": "",
        }

        # Run the agent
        result = await agent.ainvoke(initial_state)

        logger.info("manager_agent.run.end", query_type=result.get("query_type"))
        return {
            "final_report": result["final_report"],
            "companies": result.get("companies", []),
            "tickers": result.get("tickers", []),
            "financial_results": result.get("financial_results"),
            "competitor_results": result.get("competitor_results"),
            "market_intel_results": result.get("market_intel_results"),
            "query_type": result.get("query_type", "new_research"),
            "followup_agents": result.get("followup_agents", []),
        }
    except Exception as e:
        logger.error("manager_agent.run.error", error=str(e))
        return {
            "final_report": f"Error: {e}",
            "error": str(e),
            "companies": [],
            "tickers": [],
            "financial_results": None,
            "competitor_results": None,
            "market_intel_results": None,
            "query_type": "new_research",
            "followup_agents": [],
        }


def extract_tool_call_summary(agent_output: dict) -> dict:
    """Extract a lean summary of tool calls suitable for UI metadata."""
    fin = agent_output.get("financial_results") or {}
    comp = agent_output.get("competitor_results") or {}
    market = agent_output.get("market_intel_results") or {}
    return {
        "financial_tool_calls": fin.get("tool_calls", []),
        "competitor_tool_calls": comp.get("tool_calls", []),
        "market_intel_tool_calls": market.get("tool_calls", []),
    }


def run_manager_agent_sync(
    query: str,
    progress_callback: Any | None = None,
    prior_report: str | None = None,
    prior_results: dict | None = None,
) -> str:
    """Synchronous wrapper for run_manager_agent."""
    return asyncio.run(run_manager_agent(query, progress_callback, prior_report, prior_results))
