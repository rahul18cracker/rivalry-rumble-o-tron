"""Agent prompts for research team."""

from .manager_prompt import MANAGER_SYSTEM_PROMPT
from .financial_prompt import FINANCIAL_SYSTEM_PROMPT
from .competitor_prompt import COMPETITOR_SYSTEM_PROMPT

__all__ = [
    "MANAGER_SYSTEM_PROMPT",
    "FINANCIAL_SYSTEM_PROMPT",
    "COMPETITOR_SYSTEM_PROMPT",
]
