"""Journal command: archive memory files and metadata."""
import glob
import os
import shutil
from datetime import datetime

from utils.storage import build_customer_dir
from scripts.commands._meta import read_meta, write_meta


def run(customer_id: str, args: dict) -> dict:
    """Archive journal memory files and metadata to a timestamped directory."""
    base = os.path.expanduser(build_customer_dir(customer_id))
    memory_dir = os.path.join(base, "memory")
    meta_path = os.path.join(base, "journal_meta.json")

    if not os.path.exists(memory_dir) or not os.listdir(memory_dir):
        return {"status": "error", "result": None, "message": "No journal data to archive"}

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = os.path.join(base, "archive", timestamp)
    os.makedirs(archive_dir, exist_ok=True)

    archived_files = []

    for f in sorted(glob.glob(os.path.join(memory_dir, "*"))):
        if os.path.isfile(f):
            shutil.copy2(f, archive_dir)
            archived_files.append(os.path.basename(f))

    if os.path.exists(meta_path):
        shutil.copy2(meta_path, archive_dir)
        archived_files.append("journal_meta.json")

    clear_after = bool(args.get("clear", False))
    if clear_after:
        for f in glob.glob(os.path.join(memory_dir, "*")):
            os.remove(f)
        meta = read_meta(customer_id)
        if meta:
            meta["total_entries"] = 0
            write_meta(customer_id, meta)

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "archive_path": archive_dir,
            "archived_files": archived_files,
            "timestamp": timestamp,
            "cleared": clear_after,
        },
        "message": f"Archived {len(archived_files)} file(s) to {archive_dir}",
    }
