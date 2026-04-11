"""Journal command: record."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from utils.storage import build_customer_dir, build_memory_path, write_memory_file
from scripts.commands.i18n import t


EMOTION_KEYWORDS = {
    "开心": ["开心", "高兴", "愉快", "爽", "棒", "赞", "满足", "成就感", "顺利"],
    "焦虑": ["焦虑", "不安", "紧张", "压力", "着急", "慌", "担心"],
    "沮丧": ["沮丧", "失落", "难过", "失败", "糟", "郁闷", "灰心", "挫败"],
    "兴奋": ["兴奋", "激动", "期待", "冲", "热血", "燃", "憧憬"],
    "疲惫": ["累", "疲惫", "倦", "困", "burnout", "职业倦怠", "通宵", "熬夜", "睡不够"],
    "困惑": ["困惑", "迷茫", "不清", "不确定", "纠结", "没思路", "卡"],
    "放松": ["放松", "平静", "舒服", "安逸", "清闲", "自在"],
}


def generate_entry_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"JE-{today}-{suffix}"


def _detect_emotion(text: str) -> str:
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        scores[emotion] = sum(1 for kw in keywords if kw in text)
    if not scores or max(scores.values()) == 0:
        return "平静"
    return max(scores, key=scores.get)


def _is_first_entry(customer_id: str) -> bool:
    import os, glob
    memory_dir = os.path.expanduser(Path(build_customer_dir(customer_id)) / "memory")
    if not os.path.exists(memory_dir):
        return True
    files = [f for f in glob.glob(os.path.join(memory_dir, "*.md")) if os.path.basename(f) != "dreams.md"]
    # Check if only init charter exists (look for frontmatter type: entry)
    entries = []
    for f in files:
        content = Path(f).read_text(encoding="utf-8")
        if "type: entry" in content or f"## {t('record.entry_title', {'lang': 'zh'})} - JE-" in content:
            entries.append(f)
    return len(entries) == 0


def run(customer_id: str, args: dict) -> dict:
    """Record a journal entry with auto-emotion tagging and structured markdown."""
    content = args.get("content", "")
    if not content:
        return {"status": "error", "result": None, "message": t("record.missing_content", args)}

    entry_id = generate_entry_id()
    day = args.get("day", 1)
    metadata = args.get("metadata", {})
    today_str = datetime.now().strftime("%d-%m-%y")
    iso_time = datetime.now().isoformat()
    
    # Auto-detect emotion if not provided
    if "emotional_state" not in metadata:
        metadata["emotional_state"] = _detect_emotion(content)

    is_first = _is_first_entry(customer_id)
    celebration = "🎉 " if is_first else ""
    emotion_label = t("emotions." + metadata.get("emotional_state", "平静"), args)

    entry_text = f"""---
type: entry
date: {today_str}
day: {day}
entry_id: {entry_id}
emotion: {emotion_label}
---

## {t('record.entry_title', args)} - {entry_id}

**{t('record.day_label', args, day=day)}**  
**{t('record.time_label', args)}**: {iso_time}  
**{t('record.emotion_label', args)}**: {emotion_label}

### {t('record.content_label', args)}
{content}

### {t('record.metadata_label', args)}
```json
{json.dumps(metadata, indent=2, ensure_ascii=False)}
```
"""

    memory_path = build_memory_path(customer_id)
    write_result = write_memory_file(memory_path, entry_text)

    # Update meta file entry count
    try:
        import os
        meta_path = os.path.expanduser(Path(build_customer_dir(customer_id)) / "journal_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meta["total_entries"] = meta.get("total_entries", 0) + 1
            meta["last_recorded_at"] = iso_time
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if write_result["success"]:
        if is_first:
            msg = t("record.success_first", args, entry_id=entry_id, day=day)
        else:
            msg = t("record.success_normal", args, entry_id=entry_id)
        return {
            "status": "success",
            "result": {
                "entry_id": entry_id,
                "customer_id": customer_id,
                "day": day,
                "emotion": emotion_label,
                "is_first_entry": is_first,
                "memory_path": memory_path
            },
            "message": msg
        }
    return {
        "status": "error",
        "result": None,
        "message": t("record.error_message", args, error=write_result.get("error"))
    }
