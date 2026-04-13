"""Journal command: delete entry by entry_id."""
import glob
import os
import re
from pathlib import Path

from utils.storage import build_customer_dir
from scripts.commands._meta import read_meta, write_meta


def _find_entry_file(base: str, entry_id: str):
    memory_dir = os.path.join(base, "memory")
    if not os.path.exists(memory_dir):
        return None, None
    for f in sorted(glob.glob(os.path.join(memory_dir, "*.md"))):
        content = Path(f).read_text(encoding="utf-8")
        if f"entry_id: {entry_id}" in content:
            return f, content
    return None, None


def _remove_entry(content: str, entry_id: str) -> str:
    # Match entry blocks starting with ---\ntype: entry and ending before the next \n---\n or EOF.
    pattern = r"(?:^|\n\n)(---\ntype: entry.*?)(?=\n---\n|$)"
    matches = list(re.finditer(pattern, content, re.DOTALL))
    new_blocks = []
    for m in matches:
        block = m.group(1)
        if f"entry_id: {entry_id}" in block:
            continue
        new_blocks.append(block)
    if not new_blocks:
        return ""
    return "\n\n".join(new_blocks)


def run(customer_id: str, args: dict) -> dict:
    """Delete a journal entry by entry_id. Creates a .bak before modification."""
    entry_id = args.get("entry_id", "").strip()
    if not entry_id:
        return {"status": "error", "result": None, "message": "entry_id is required"}

    base = os.path.expanduser(build_customer_dir(customer_id))
    file_path, content = _find_entry_file(base, entry_id)
    if file_path is None:
        return {"status": "error", "result": None, "message": f"Entry {entry_id} not found"}

    new_content = _remove_entry(content, entry_id)

    # Backup before mutation
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        import shutil

        shutil.copy2(file_path, file_path + ".bak")

    if not new_content.strip():
        os.remove(file_path)
    else:
        Path(file_path).write_text(new_content, encoding="utf-8")

    meta = read_meta(customer_id)
    if meta:
        meta["total_entries"] = max(0, meta.get("total_entries", 0) - 1)
        write_meta(customer_id, meta)

    return {
        "status": "success",
        "result": {
            "entry_id": entry_id,
            "customer_id": customer_id,
            "file": file_path,
            "file_removed": not new_content.strip(),
        },
        "message": f"Entry {entry_id} deleted",
    }
