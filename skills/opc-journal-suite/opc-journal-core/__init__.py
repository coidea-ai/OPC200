"""OPC Journal Core - Core journaling functionality for OPC200.

This package provides essential journal operations including:
- Journal initialization and configuration
- Entry recording with metadata and tags
- Entry searching and filtering
- Journal export functionality

Example:
    >>> from opc_journal_core.scripts import init, record, search, export
    >>> result = init({"customer_id": "opc-001", "input": {}})
"""

from opc_journal_core.scripts import init, record, search, export

__version__ = "2.2.2"
__all__ = [
    "init",
    "record",
    "search",
    "export",
    "__version__",
]
