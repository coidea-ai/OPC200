"""OPC Journal Suite package.

This package provides a unified entry point for the OPC Journal Suite,
routing user intents to appropriate sub-skills.

Version: 2.2.2
"""

__version__ = "2.2.2"

# Package exports - use absolute imports for CI compatibility
try:
    # When installed as a package
    from opc_journal_suite.scripts.coordinate import main as coordinate
    from opc_journal_suite.scripts.coordinate import detect_intent, get_skill_for_intent
except ImportError:
    # When running directly from source (development mode)
    import sys
    from pathlib import Path
    scripts_path = str(Path(__file__).parent / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from coordinate import main as coordinate
    from coordinate import detect_intent, get_skill_for_intent

__all__ = ['coordinate', 'detect_intent', 'get_skill_for_intent']
