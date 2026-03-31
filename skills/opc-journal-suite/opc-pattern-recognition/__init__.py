"""OPC Pattern Recognition - Pattern analysis for OPC200.

This package provides pattern recognition:
- Analyzer initialization
- Pattern analysis
- Outlier detection

Example:
    >>> from opc_pattern_recognition.scripts import init, analyze, detect_outliers
    >>> result = analyze({"customer_id": "opc-001", "input": {...}})
"""

from opc_pattern_recognition.scripts import init, analyze, detect_outliers

__version__ = "2.2.2"
__all__ = [
    "init",
    "analyze",
    "detect_outliers",
    "__version__",
]
