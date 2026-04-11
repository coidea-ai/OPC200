"""Journal command: search."""
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
        "message": f"Search prepared for {customer_id}: {query or '(all entries)' }"
    }
