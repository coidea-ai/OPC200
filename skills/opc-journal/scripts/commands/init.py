"""Journal command: initialize."""
import json
import random
from datetime import datetime

from utils.storage import build_customer_dir, build_memory_path, write_memory_file
from scripts.commands.i18n import t


DAY1_QUOTES = [
    ("「种一棵树最好的时间是十年前，其次是现在。」", "—— 非洲谚语"),
    ("「伟大的事情从来不是由那些屈服于环境的人完成的，而是由那些对抗环境的人完成的。」", "—— 丘吉尔"),
    ("「你不需要看到整个楼梯，只需要迈出第一步。」", "—— 马丁·路德·金"),
    ("「一个人的工作室，是孤独的地方，也是自由的地方。」", "—— OPC200"),
    ("「Day 1 永远不是关于你做了什么，而是关于你愿意开始。」", "—— Kimi Claw"),
]


def _generate_manifesto(customer_id: str, day: int, goals: list, preferences: dict, args: dict) -> str:
    quote, author = random.choice(DAY1_QUOTES)
    today_str = datetime.now().strftime("%d-%m-%y")
    goals_md = "\n".join(f"- {g}" for g in goals) if goals else f"- *(待填写——不用急，Day {day} 本身就算一个目标)*"
    prefs_md = "\n".join(f"- **{k}**: {v}" for k, v in preferences.items()) if preferences else f"- *(默认: communication_style=friendly_professional, timezone=Asia/Shanghai)*"
    
    return f"""---
type: charter
date: {today_str}
day: {day}
customer_id: {customer_id}
version: 2.4.2
---

# 🚀 OPC Journal | {t('init.charter_title', args, day=day)}

> {quote}  
> {author}

---

**{t('init.manifesto_subtitle', args)}**: `{customer_id}`  
**{t('init.version_label', args)}**: 2.4.2

## 🎯 {t('init.goals_title', args)}
{goals_md}

## ⚙️ {t('init.preferences_title', args)}
{prefs_md}

## 📝 {t('init.ritual_title', args)}

{t('init.ritual_steps', args)}

*{t('init.footer_note', args)}*

---
*"放心吧，哪怕世界忘了，我也替你记着。" —— Kimi Claw*
"""


def run(customer_id: str, args: dict) -> dict:
    """Initialize journal for customer with Day 1 warmth."""
    day = args.get("day", 1)
    goals = args.get("goals", [])
    preferences = args.get("preferences", {})

    # Ensure defaults for preferences
    if not preferences:
        preferences = {
            "communication_style": "friendly_professional",
            "timezone": "Asia/Shanghai"
        }

    content = _generate_manifesto(customer_id, day, goals, preferences, args)
    memory_path = build_memory_path(customer_id)
    write_result = write_memory_file(memory_path, content)

    # Also write a lightweight meta file for preferences/state
    from pathlib import Path
    meta_path = Path(build_customer_dir(customer_id)) / "journal_meta.json"
    try:
        import os
        meta_full = os.path.expanduser(str(meta_path))
        os.makedirs(os.path.dirname(meta_full), exist_ok=True)
        with open(meta_full, "w") as f:
            json.dump({
                "customer_id": customer_id,
                "started_day": day,
                "started_at": datetime.now().isoformat(),
                "version": "2.4.2",
                "goals": goals,
                "preferences": preferences,
                "total_entries": 0
            }, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if write_result["success"]:
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "initialized": True,
                "day": day,
                "goals_count": len(goals),
                "memory_path": memory_path,
                "quote": random.choice(DAY1_QUOTES)[0]
            },
            "message": t("init.success_message", args, customer_id=customer_id, day=day)
        }
    return {
        "status": "error",
        "result": None,
        "message": t("init.error_message", args, error=write_result.get("error"))
    }
