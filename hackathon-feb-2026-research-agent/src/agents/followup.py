"""Follow-up routing and synthesis logic for conversational follow-ups."""

import json

from ..logging_config import get_logger
from ..prompts.followup_prompt import (
    FOLLOWUP_AGENT_TASK_TEMPLATE,
    FOLLOWUP_SYNTHESIS_PROMPT,
    ROUTE_QUERY_PROMPT,
)

logger = get_logger(__name__)

# Valid agent names for follow-up re-runs
VALID_AGENTS = {"financial", "competitor", "market_intel"}


def route_query(user_query: str, prior_report: str | None, llm) -> dict:
    """Classify query type and determine execution path.

    Returns:
        dict with keys: query_type, agents_needed, focused_task, reasoning
    """
    # No prior report → always new research
    if not prior_report:
        logger.info("followup.route.no_prior_report")
        return {
            "query_type": "new_research",
            "agents_needed": [],
            "focused_task": user_query,
            "reasoning": "No prior report — full research pipeline required.",
        }

    prompt = ROUTE_QUERY_PROMPT.format(
        prior_report=prior_report,
        user_query=user_query,
    )

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        content = response.content.strip()

        # Strip markdown code fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        parsed = json.loads(content.strip())

        query_type = parsed.get("query_type", "new_research")
        if query_type not in ("new_research", "followup_with_agents", "followup_context_only"):
            query_type = "new_research"

        agents_needed = [a for a in parsed.get("agents_needed", []) if a in VALID_AGENTS]
        focused_task = parsed.get("focused_task", user_query)
        reasoning = parsed.get("reasoning", "")

        # If followup_with_agents but no valid agents listed, fall back to new_research
        if query_type == "followup_with_agents" and not agents_needed:
            logger.warning("followup.route.no_valid_agents", parsed=parsed)
            query_type = "new_research"

        logger.info(
            "followup.route.classified",
            query_type=query_type,
            agents_needed=agents_needed,
        )
        return {
            "query_type": query_type,
            "agents_needed": agents_needed,
            "focused_task": focused_task,
            "reasoning": reasoning,
        }

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.warning("followup.route.parse_error", error=str(e))
        return {
            "query_type": "new_research",
            "agents_needed": [],
            "focused_task": user_query,
            "reasoning": f"Classification failed ({type(e).__name__}), falling back to full research.",
        }
    except Exception as e:
        logger.error("followup.route.llm_error", error=str(e))
        return {
            "query_type": "new_research",
            "agents_needed": [],
            "focused_task": user_query,
            "reasoning": f"LLM error ({type(e).__name__}), falling back to full research.",
        }


def build_focused_task(
    agent_type: str,
    followup_query: str,
    prior_report: str,
    companies: list[str],
) -> str:
    """Build a context-rich task string for a sub-agent re-run.

    Uses FOLLOWUP_AGENT_TASK_TEMPLATE to include prior context + focused question.
    """
    # Determine focused task description based on agent type
    task_descriptions = {
        "financial": f"Retrieve updated financial data and metrics relevant to: {followup_query}",
        "competitor": f"Research competitive positioning details relevant to: {followup_query}",
        "market_intel": f"Gather market intelligence and trends relevant to: {followup_query}",
    }
    focused_task = task_descriptions.get(agent_type, followup_query)

    return FOLLOWUP_AGENT_TASK_TEMPLATE.format(
        companies=", ".join(companies),
        prior_findings=prior_report[:2000] if len(prior_report) > 2000 else prior_report,
        followup_query=followup_query,
        focused_task=focused_task,
    )


def _summarize_results(results: dict | None) -> str:
    """Extract a text summary from agent results dict."""
    if not results:
        return "No results available."
    parts = []
    for agent_key in ("financial_results", "competitor_results", "market_intel_results"):
        agent_data = results.get(agent_key)
        if isinstance(agent_data, dict):
            response_text = agent_data.get("response", "")
            if response_text:
                parts.append(response_text)
    return "\n\n".join(parts) if parts else "No detailed results available."


def synthesize_followup(
    query: str,
    prior_report: str,
    prior_results: dict | None,
    new_results: dict | None,
    llm,
) -> str:
    """Generate focused conversational response from context + optional new data."""
    prompt = FOLLOWUP_SYNTHESIS_PROMPT.format(
        prior_report=prior_report,
        prior_results_summary=_summarize_results(prior_results),
        new_results_summary=_summarize_results(new_results) if new_results else "No new data gathered.",
        followup_query=query,
    )

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        return response.content
    except Exception as e:
        logger.error("followup.synthesize.error", error=str(e))
        return f"I wasn't able to generate a follow-up answer: {e}"
