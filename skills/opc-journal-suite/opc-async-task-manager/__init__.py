"""OPC Async Task Manager - Asynchronous task management for OPC200.

This package provides task scheduling and management:
- Task initialization and configuration
- Task creation and submission
- Task execution handling
- Task status tracking

Example:
    >>> from opc_async_task_manager.scripts import init, create, execute, status
    >>> result = create({"customer_id": "opc-001", "input": {...}})
"""

from opc_async_task_manager.scripts import init, create, execute, status

__version__ = "2.2.2"
__all__ = [
    "init",
    "create",
    "execute",
    "status",
    "__version__",
]
