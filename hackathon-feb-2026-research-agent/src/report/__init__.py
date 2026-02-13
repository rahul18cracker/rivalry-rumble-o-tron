"""Report generation for research output."""

from .generator import generate_report
from .templates import REPORT_TEMPLATE

__all__ = ["generate_report", "REPORT_TEMPLATE"]
