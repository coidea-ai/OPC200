"""Journal command: status."""
import glob
import os
import re
from datetime import datetime
from pathlib import Path

from utils.storage import build_customer_dir, build_memory_path
from scripts.commands._meta import get_language, read_meta


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

    meta = read_meta(customer_id)
    started_day = meta.get("started_day", 1)
    lang = get_language(customer_id)

    if entry_count == 0:
        journal_active = False
        latest_display = "No entries yet" if lang == "en" else "还没有正式记录"
        if lang == "en":
            message = f"🌱 {customer_id}'s Journal is active (Day {started_day}), but no entries yet. Next step: /opc-journal record \"One thing you did today\""
        else:
            message = f"🌱 {customer_id} 的 Journal 已激活（第 {started_day} 天），但还没有正式记录。下一步：/opc-journal record \"今天完成的第一件事\""
    else:
        journal_active = True
        latest_display = latest
        if lang == "en":
            message = f"📔 {customer_id} started on Day {started_day} and has recorded {entry_count} entries. Latest: {latest}."
        else:
            message = f"📔 {customer_id} 从第 {started_day} 天开始，已经记录了 {entry_count} 条。最新：{latest}。"

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
