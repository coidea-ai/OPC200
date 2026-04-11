"""Journal command: status."""
import glob
import os

from utils.storage import build_customer_dir, build_memory_path


def run(customer_id: str, args: dict) -> dict:
    """Show journal status for customer."""
    base = os.path.expanduser(build_customer_dir(customer_id))
    memory_dir = os.path.join(base, "memory")
    entry_count = 0
    if os.path.exists(memory_dir):
        entry_count = len(glob.glob(os.path.join(memory_dir, "*.md")))

    latest = "No entries yet"
    if entry_count > 0:
        files = sorted(glob.glob(os.path.join(memory_dir, "*.md")))
        latest = os.path.basename(files[-1]).replace(".md", "")

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "total_entries": entry_count,
            "latest_entry_date": latest,
            "journal_active": entry_count > 0
        },
        "message": f"{customer_id} journal: {entry_count} entries, latest: {latest}"
    }
