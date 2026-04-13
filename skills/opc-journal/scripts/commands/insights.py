"""Journal command: insights (raw context for LLM interpretation)."""
import glob
import os
import re
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file
from scripts.commands._meta import get_language


def _find_sources(customer_id: str):
    sources = []
    base = build_customer_dir(customer_id)
    dreams = f"{base}/dreams.md"
    if os.path.exists(os.path.expanduser(dreams)):
        sources.append(("dreams", dreams))
    memory_dir = f"{base}/memory"
    if os.path.exists(os.path.expanduser(memory_dir)):
        files = glob.glob(f"{memory_dir}/*.md")
        files.sort(key=lambda f: _parse_file_date(f))
        sources.extend([("memory", f) for f in files])
    return sources


def _parse_file_date(path: str) -> str:
    basename = os.path.basename(path)
    m = re.search(r"(\d{2}-\d{2}-\d{2})\.md$", basename)
    if m:
        return m.group(1)
    return "00-00-00"


def _read_recent(sources: list, days: int = 7):
    dated = []
    for source_type, s in sources:
        file_date = _parse_file_date(s)
        if file_date != "00-00-00":
            dated.append((file_date, source_type, s))
        else:
            mtime_str = datetime.fromtimestamp(os.path.getmtime(s)).strftime("%d-%m-%y")
            dated.append((mtime_str, source_type, s))
    dated.sort(key=lambda x: datetime.strptime(x[0], "%d-%m-%y"))
    recent = dated[-min(days, len(dated)):]
    contents = []
    dates_read = []
    for d, source_type, path in recent:
        res = read_memory_file(path)
        if res.get("success"):
            contents.append(res["content"])
            dates_read.append({"date": d, "type": source_type, "path": path})
    return "\n\n".join(contents), dates_read


def run(customer_id: str, args: dict) -> dict:
    """Return recent journal context for the caller (LLM) to generate insights dynamically."""
    day = args.get("day", 1)
    days_back = args.get("days_back", 7)
    lang = get_language(customer_id)
    sources = _find_sources(customer_id)

    if not sources:
        return {
            "status": "success",
            "result": {
                "day": day,
                "customer_id": customer_id,
                "language": lang,
                "sources": [],
                "raw_text": "",
                "signal_counts": {},
            },
            "message": "No memory sources available",
        }

    raw_text, dates_read = _read_recent(sources, days_back)
    emotion_tokens = re.findall(
        r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动|happy|anxious|confused|frustrated|excited|tired|satisfied|worried|relaxed|sad|nervous)",
        raw_text,
        re.IGNORECASE,
    )
    emotion_counts = {}
    for emo in emotion_tokens:
        emotion_counts[emo.lower()] = emotion_counts.get(emo.lower(), 0) + 1

    activity_mentions = len([l for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")])

    signal_counts = {
        "pivot_signals": len(re.findall(r"(没效果|traction|方向|转型|换方向|PMF|验证失败|pivot|direction|validation failed)", raw_text, re.IGNORECASE)),
        "momentum_signals": len(re.findall(r"(完成|发布|上线|销售|收款|签约|里程碑|突破|completed|shipped|launched|sale|milestone|breakthrough)", raw_text, re.IGNORECASE)),
        "overload_signals": len(re.findall(r"(太多|忙不过来|焦虑|疲惫|burnout|通宵|加班|overwhelm|burnout|exhausted|too much)", raw_text, re.IGNORECASE)),
        "isolation_signals": len(re.findall(r"(没人|孤独|一个人|没反馈|迷茫|没思路|lonely|alone|no feedback|lost|isolated)", raw_text, re.IGNORECASE)),
        "learning_signals": len(re.findall(r"(学会|掌握了|第一次|新技能|恍然大悟|理解|搞懂了|learned|first time|new skill|figured out|understood)", raw_text, re.IGNORECASE)),
        "emotion_mentions": emotion_counts,
        "activity_lines": activity_mentions,
    }

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "day": day,
            "language": lang,
            "days_back": days_back,
            "sources": dates_read,
            "raw_text": raw_text,
            "signal_counts": signal_counts,
            "generated_at": datetime.now().isoformat(),
            "data_source": "openclaw_dreams_memory",
        },
        "message": f"Insight context prepared for Day {day} from the last {len(dates_read)} source(s).",
    }
