"""OPC Journal Suite package.

This package provides a unified entry point for the OPC Journal Suite,
routing user intents to appropriate sub-skills.

Version: 2.2.2
"""

__version__ = "2.2.2"

# Package-level exports (imported lazily to avoid import errors)
__all__ = ['coordinate', 'detect_intent', 'get_skill_for_intent']

# Note: Use direct script execution for actual skill operation:
#   python -m opc_journal_suite.scripts.coordinate
#   python opc-journal-suite/scripts/coordinate.py
