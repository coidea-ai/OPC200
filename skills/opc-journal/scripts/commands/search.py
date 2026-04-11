"""Journal command: search."""
from scripts.commands.i18n import t


def run(customer_id: str, args: dict) -> dict:
    """Search journal entries."""
    query = args.get("query", "")
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "query": query,
            "tool_hint": "Use 'memory_search' tool to find relevant entries"
        },
        "message": t("search.success_message", args, customer_id=customer_id, query=query or "全部记录")
    }
