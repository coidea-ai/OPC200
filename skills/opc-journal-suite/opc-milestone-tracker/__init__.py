"""OPC Milestone Tracker - Milestone detection and tracking for OPC200.

This package provides milestone management:
- Tracker initialization
- Milestone detection

Note: All operations are local-only. No network calls or external sharing.

Example:
    >>> from opc_milestone_tracker.scripts import init, detect
    >>> result = detect({"customer_id": "opc-001", "input": {...}})
"""

from opc_milestone_tracker.scripts import init, detect

__version__ = "2.2.2"
__all__ = [
    "init",
    "detect",
    "__version__",
]
