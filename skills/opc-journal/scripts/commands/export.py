"""Journal command: export."""
from scripts.commands._meta import get_language


def run(customer_id: str, args: dict) -> dict:
    """Export journal entries."""
    export_format = args.get("format", "markdown")
    lang = get_language(customer_id)
    msg = f"Export prepared for {customer_id} ({export_format})" if lang == "en" else f"已为 {customer_id} 准备导出（格式：{export_format}）"
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "export_format": export_format,
            "time_range": args.get("time_range", "all"),
            "tool_hint": "Use 'memory_search' and 'read' to retrieve entries, then format"
        },
        "message": msg
    }
