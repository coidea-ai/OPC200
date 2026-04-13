"""Journal command: search."""
from scripts.commands._meta import get_language


def run(customer_id: str, args: dict) -> dict:
    """Search journal entries."""
    query = args.get("query", "")
    lang = get_language(customer_id)
    display_query = query or ("all entries" if lang == "en" else "全部记录")
    msg = f"Search prepared for {customer_id}: {display_query}" if lang == "en" else f"已为 {customer_id} 准备搜索：{display_query}"
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "query": query,
            "tool_hint": "Use 'memory_search' tool to find relevant entries"
        },
        "message": msg
    }
