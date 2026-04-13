"""Minimal meta helpers for opc-journal commands."""
import json
import os
from pathlib import Path

from utils.storage import build_customer_dir


def read_meta(customer_id: str) -> dict:
    try:
        path = os.path.expanduser(Path(build_customer_dir(customer_id)) / "journal_meta.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_language(customer_id: str) -> str:
    meta = read_meta(customer_id)
    lang = meta.get("language", "")
    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("en"):
        return "en"
    return "zh"


def _has_chinese(texts: list) -> bool:
    combined = " ".join(str(t) for t in texts if t)
    return any("\u4e00" <= c <= "\u9fff" for c in combined)


def detect_language(texts: list) -> str:
    return "zh" if _has_chinese(texts) else "en"


def write_meta(customer_id: str, data: dict) -> bool:
    try:
        path = os.path.expanduser(Path(build_customer_dir(customer_id)) / "journal_meta.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
