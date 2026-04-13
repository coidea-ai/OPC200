"""Journal command: analyze (raw signal extraction for LLM interpretation)."""
import glob
import os
import re
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file
from scripts.commands._meta import get_language


def _parse_file_date(path: str) -> str:
    basename = os.path.basename(path)
    m = re.search(r"(\d{2}-\d{2}-\d{2})\.md$", basename)
    if m:
        return m.group(1)
    return "00-00-00"


def _find_sources(customer_id: str):
    sources = []
    base = build_customer_dir(customer_id)
    dreams = f"{base}/dreams.md"
    if os.path.exists(os.path.expanduser(dreams)):
        sources.append(("dreams", dreams))
    memory_dir = f"{base}/memory"
    if os.path.exists(os.path.expanduser(memory_dir)):
        files = glob.glob(f"{memory_dir}/*.md")
        files.sort(key=lambda f: datetime.strptime(_parse_file_date(f), "%d-%m-%y"))
        sources.extend([("memory", f) for f in files])
    return sources


def run(customer_id: str, args: dict) -> dict:
    """Return structured raw signals and context for the caller (LLM) to interpret dynamically."""
    days = args.get("days", 7)
    lang = get_language(customer_id)
    sources = _find_sources(customer_id)
    if not sources:
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "analysis_type": args.get("dimension", "general"),
                "language": lang,
                "files": [],
                "raw_text": "",
                "signal_summary": {
                    "sources_count": 0,
                    "total_lines": 0,
                },
            },
            "message": "No memory sources available",
        }

    texts = []
    files_meta = []
    for source_type, path in sources[-min(days * 2, len(sources)): ]:
        res = read_memory_file(path)
        if res.get("success"):
            texts.append(res["content"])
            files_meta.append({
                "type": source_type,
                "path": path,
                "date": _parse_file_date(path),
            })

    raw_text = "\n".join(texts)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")]

    # Return lightweight structural signals only — NO hardcoded labels or interpretations.
    signal_summary = {
        "total_lines": len(lines),
        "days_span": days,
        "sources_count": len(files_meta),
        "emotion_mentions": _extract_tokens(raw_text, r"(happy|anxious|confused|frustrated|excited|tired|satisfied|worried|nervous|relaxed|sad)"),
        "decision_fragments": _extract_fragments(raw_text, r"(decided|choose|switch|adopt|finalize|hesitate)(.*?)(?:;|\n|\.)"),
        "milestone_fragments": _extract_fragments(raw_text, r"(completed|launched|shipped|sale|signed|revenue|MVP|prototype|milestone|breakthrough)(.*?)(?:;|\n|\.)"),
        "blocker_fragments": _extract_fragments(raw_text, r"(stuck|blocked|bottleneck|failed|error|bug|issue)(.*?)(?:;|\n|\.)"),
        "help_seeking_count": len(re.findall(r"(ask|discuss|delegate|help)", raw_text, re.IGNORECASE)),
    }

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "analysis_type": args.get("dimension", "general"),
            "language": lang,
            "files": files_meta,
            "raw_text": raw_text,
            "signal_summary": signal_summary,
        },
        "message": f"Pattern analysis context prepared for {customer_id}",
    }


def _extract_tokens(text: str, pattern: str) -> dict:
    found = re.findall(pattern, text, re.IGNORECASE)
    counts = {}
    for token in found:
        key = token.lower() if isinstance(token, str) else token[0].lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def _extract_fragments(text: str, pattern: str, max_len: int = 120) -> list:
    matches = re.finditer(pattern, text, re.IGNORECASE)
    fragments = []
    for m in matches:
        frag = m.group(0).strip().replace("\n", " ")
        if len(frag) > 3:
            fragments.append(frag[:max_len])
    return fragments[:10]
