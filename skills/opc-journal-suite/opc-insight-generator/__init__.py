"""OPC Insight Generator - Daily insights and summaries for OPC200.

This package provides insight generation:
- Generator initialization
- Daily summary generation

Example:
    >>> from opc_insight_generator.scripts import init, daily_summary
    >>> result = daily_summary({"customer_id": "opc-001", "input": {...}})
"""

from opc_insight_generator.scripts import init, daily_summary

__version__ = "2.2.2"
__all__ = [
    "init",
    "daily_summary",
    "__version__",
]
