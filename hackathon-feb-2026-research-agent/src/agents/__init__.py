"""Agent implementations for research team."""

from .competitor import run_competitor_agent
from .financial import run_financial_agent
from .followup import build_focused_task, route_query, synthesize_followup
from .manager import run_manager_agent
from .market_intel import run_market_intel_agent

__all__ = [
    "run_manager_agent",
    "run_financial_agent",
    "run_competitor_agent",
    "run_market_intel_agent",
    "route_query",
    "build_focused_task",
    "synthesize_followup",
]
