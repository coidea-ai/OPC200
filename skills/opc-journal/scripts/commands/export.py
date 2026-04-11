"""Journal command: export."""
from scripts.commands.i18n import t


def run(customer_id: str, args: dict) -> dict:
    """Export journal entries."""
    export_format = args.get("format", "markdown")
    time_range = args.get("time_range", "all")
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "export_format": export_format,
            "time_range": time_range,
            "tool_hint": "Use 'memory_search' and 'read' to retrieve entries, then format"
        },
        "message": t("export.success_message", args, customer_id=customer_id, fmt=export_format)
    }
