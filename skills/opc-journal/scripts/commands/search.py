"""Journal command: search."""
from scripts.commands._meta import get_language


def run(customer_id: str, args: dict) -> dict:
    """Search journal entries."""
    query = args.get("query", "")
    display_query = query or "all entries"
    msg = f"Search prepared for {customer_id}: {display_query}"
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "query": query,
            "tool_hint": "Use 'memory_search' tool to find relevant entries"
        },
        "message": msg
    }
