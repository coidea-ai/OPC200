"""Journal command: record."""
import glob
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from utils.storage import build_customer_dir, build_memory_path, write_memory_file
from scripts.commands._meta import get_language, read_meta, write_meta


def generate_entry_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"JE-{today}-{suffix}"


def _analyze_emotion(text: str, lang: str = "zh") -> str:
    """Dynamic emotion profiling based on energy, tension, valence, fatigue."""
    t = text.lower()
    energy = any(k in t for k in ["兴奋", "激动", "期待", "燃", "冲", "热血", "excited", "thrilled", "pumped", "energized"])
    tension = any(k in t for k in ["焦虑", "紧张", "压力", "慌", "担心", "纠结", "anxious", "stressed", "nervous", "tense", "worried"])
    positive = any(k in t for k in ["开心", "满足", "顺利", "搞定", "赞", "棒", "happy", "glad", "satisfied", "smooth", "great", "good"])
    negative = any(k in t for k in ["沮丧", "失落", "难过", "失败", "郁闷", "frustrated", "sad", "depressed", "down", "disappointed"])
    fatigue = any(k in t for k in ["累", "疲惫", "困", "burnout", "通宵", "熬夜", "tired", "exhausted", "sleepy", "burned out"])

    if lang == "en":
        if energy and tension and positive:
            return "Excited yet tightly wound, like the moments before a sprint"
        if energy and positive and not tension:
            return "High energy and full of momentum"
        if fatigue and tension:
            return "Running on fumes — a pause button is needed"
        if fatigue and not tension:
            return "Weary, but the pace is still manageable"
        if tension and negative:
            return "Heavy, as if weighed down by unresolved issues"
        if tension and not negative:
            return "A bit tense, but still pushing forward"
        if positive and not tension:
            return "Calm and content"
        if negative and not tension:
            return "Slightly low, but no longer fighting intensely"
        return "Calm and steady, no strong emotional ripples"

    # zh default
    if energy and tension and positive:
        return "兴奋中带着一丝紧绷，像是冲刺前的状态"
    if energy and positive and not tension:
        return "状态高涨，充满行动力"
    if fatigue and tension:
        return "身心俱疲，需要按下暂停键"
    if fatigue and not tension:
        return "有些倦怠，但节奏尚可控"
    if tension and negative:
        return "情绪沉重，像是被未解决的问题压着"
    if tension and not negative:
        return "有些紧绷，但仍在向前推进"
    if positive and not tension:
        return "平和而满足"
    if negative and not tension:
        return "略带低落，但已经没有激烈对抗"
    return "平静如水，没有强烈的情绪波动"


def _is_first_entry(customer_id: str) -> bool:
    memory_dir = os.path.expanduser(Path(build_customer_dir(customer_id)) / "memory")
    if not os.path.exists(memory_dir):
        return True
    files = [f for f in glob.glob(os.path.join(memory_dir, "*.md")) if os.path.basename(f) != "dreams.md"]
    for f in files:
        content = Path(f).read_text(encoding="utf-8")
        if "type: entry" in content:
            return False
    return True


def run(customer_id: str, args: dict) -> dict:
    """Record a journal entry with auto-emotion tagging and structured markdown."""
    content = args.get("content", "")
    lang = get_language(customer_id)
    if not content:
        missing_msg = "content is required" if lang == "en" else "请提供记录内容（content 不能为空）"
        return {"status": "error", "result": None, "message": missing_msg}

    entry_id = generate_entry_id()
    day = args.get("day", 1)
    metadata = args.get("metadata", {})
    today_str = datetime.now().strftime("%d-%m-%y")
    iso_time = datetime.now().isoformat()

    # Auto-detect emotion if not provided
    if "emotional_state" not in metadata:
        metadata["emotional_state"] = _analyze_emotion(content, lang)

    is_first = _is_first_entry(customer_id)
    emotion_label = metadata.get("emotional_state", _analyze_emotion(content, lang))

    if lang == "en":
        entry_text = f"""---
type: entry
date: {today_str}
day: {day}
entry_id: {entry_id}
emotion: {emotion_label}
---

## Journal Entry - {entry_id}

**Day {day}**  
**Time**: {iso_time}  
**Emotion**: {emotion_label}

### Content
{content}

### Metadata
```json
{json.dumps(metadata, indent=2, ensure_ascii=False)}
```
"""
    else:
        entry_text = f"""---
type: entry
date: {today_str}
day: {day}
entry_id: {entry_id}
emotion: {emotion_label}
---

## 日记条目 - {entry_id}

**第 {day} 天**  
**时间**: {iso_time}  
**情绪**: {emotion_label}

### 内容
{content}

### 元数据
```json
{json.dumps(metadata, indent=2, ensure_ascii=False)}
```
"""

    memory_path = build_memory_path(customer_id)
    write_result = write_memory_file(memory_path, entry_text)

    # Update meta file entry count
    meta = read_meta(customer_id)
    if meta:
        meta["total_entries"] = meta.get("total_entries", 0) + 1
        meta["last_recorded_at"] = iso_time
        write_meta(customer_id, meta)

    if write_result["success"]:
        if lang == "en":
            if is_first:
                msg = f"🎉 Entry {entry_id} recorded — that's your first real entry. Day {day} is officially in motion."
            else:
                msg = f"Entry {entry_id} recorded"
        else:
            if is_first:
                msg = f"🎉 已记录条目 {entry_id}——这是你的第一条真实记录。第 {day} 天正式启程。"
            else:
                msg = f"已记录条目 {entry_id}"
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

    err_msg = f"Failed to write entry: {write_result.get('error')}" if lang == "en" else f"写入条目失败：{write_result.get('error')}"
    return {
        "status": "error",
        "result": None,
        "message": err_msg
    }
