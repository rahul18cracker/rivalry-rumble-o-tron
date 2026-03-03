"""Agent prompts for research team."""

from .competitor_prompt import COMPETITOR_SYSTEM_PROMPT
from .financial_prompt import FINANCIAL_SYSTEM_PROMPT
from .followup_prompt import (
    FOLLOWUP_AGENT_TASK_TEMPLATE,
    FOLLOWUP_SYNTHESIS_PROMPT,
    ROUTE_QUERY_PROMPT,
)
from .manager_prompt import MANAGER_SYSTEM_PROMPT
from .market_intel_prompt import MARKET_INTEL_SYSTEM_PROMPT

__all__ = [
    "MANAGER_SYSTEM_PROMPT",
    "FINANCIAL_SYSTEM_PROMPT",
    "COMPETITOR_SYSTEM_PROMPT",
    "MARKET_INTEL_SYSTEM_PROMPT",
    "ROUTE_QUERY_PROMPT",
    "FOLLOWUP_SYNTHESIS_PROMPT",
    "FOLLOWUP_AGENT_TASK_TEMPLATE",
]
