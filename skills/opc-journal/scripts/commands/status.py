"""Journal command: status."""
import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path

from utils.storage import build_customer_dir, build_memory_path
from scripts.commands.i18n import t


def _read_meta(customer_id: str) -> dict:
    try:
        meta_path = os.path.expanduser(Path(build_customer_dir(customer_id)) / "journal_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _parse_md_date(basename: str) -> str:
    m = re.search(r"(\d{2}-\d{2}-\d{2})\.md$", basename)
    if m:
        return m.group(1)
    return "00-00-00"


def run(customer_id: str, args: dict) -> dict:
    """Show journal status for customer."""
    base = os.path.expanduser(build_customer_dir(customer_id))
    memory_dir = os.path.join(base, "memory")
    entry_count = 0
    first_entry_date = None
    latest = None

    if os.path.exists(memory_dir):
        files = glob.glob(os.path.join(memory_dir, "*.md"))
        # Sort by dd-mm-yy date descending for reliable latest order
        files.sort(key=lambda f: _parse_md_date(os.path.basename(f)), reverse=True)
        for f in files:
            content = Path(f).read_text(encoding="utf-8")
            if "type: entry" in content:
                entry_count += 1
                date_str = _parse_md_date(os.path.basename(f))
                if latest is None:
                    latest = date_str
                if first_entry_date is None:
                    first_entry_date = date_str

    meta = _read_meta(customer_id)
    started_day = meta.get("started_day", 1)

    if entry_count == 0:
        message = t("status.empty_message", args, customer_id=customer_id, started_day=started_day)
        journal_active = False
        latest_display = t("status.no_entries", args)
    else:
        message = t("status.active_message", args, customer_id=customer_id, started_day=started_day, entry_count=entry_count, latest=latest)
        journal_active = True
        latest_display = latest

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "started_day": started_day,
            "total_entries": entry_count,
            "first_entry_date": first_entry_date or "N/A",
            "latest_entry_date": latest_display,
            "journal_active": journal_active
        },
        "message": message
    }
