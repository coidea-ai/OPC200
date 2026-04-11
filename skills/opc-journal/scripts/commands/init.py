"""Journal command: initialize."""
import json
import random
from datetime import datetime

from utils.storage import build_customer_dir, build_memory_path, write_memory_file


DAY1_QUOTES = [
    ("「种一棵树最好的时间是十年前，其次是现在。」", "—— 非洲谚语"),
    ("「伟大的事情从来不是由那些屈服于环境的人完成的，而是由那些对抗环境的人完成的。」", "—— 丘吉尔"),
    ("「你不需要看到整个楼梯，只需要迈出第一步。」", "—— 马丁·路德·金"),
    ("「一个人的工作室，是孤独的地方，也是自由的地方。」", "—— OPC200"),
    ("「Day 1 永远不是关于你做了什么，而是关于你愿意开始。」", "—— Kimi Claw"),
]


def _generate_manifesto(customer_id: str, day: int, goals: list, preferences: dict) -> str:
    quote, author = random.choice(DAY1_QUOTES)
    today_str = datetime.now().strftime("%d-%m-%y")
    goals_md = "\n".join(f"- {g}" for g in goals) if goals else "- *(待填写——不用急，Day 1 本身就算一个目标)*"
    prefs_md = "\n".join(f"- **{k}**: {v}" for k, v in preferences.items()) if preferences else "- *(默认: communication_style=friendly_professional, timezone=Asia/Shanghai)*"
    
    return f"""---
type: charter
date: {today_str}
day: {day}
customer_id: {customer_id}
version: 2.4.0
---

# 🚀 OPC Journal | 第 {day} 天章程

> {quote}  
> {author}

---

**用户**: `{customer_id}`  
**初始化日期**: {today_str}  
**版本**: 2.4.0

## 🎯 目标
{goals_md}

## ⚙️ 偏好设置
{prefs_md}

## 📝 首日仪式

1. 完成一件小事（哪怕只是把想法写出来）
2. 用 `/opc-journal record "..."` 告诉我
3. 明天回来看看状态

*这不是日记本，这是你创业的飞行器黑匣子。*

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

    content = _generate_manifesto(customer_id, day, goals, preferences)
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
                "version": "2.4.0",
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
            "message": f"🎉 {customer_id} 的 Journal 已初始化。第 {day} 天正式开始。试试：/opc-journal record \"你的第一步\""
        }
    return {
        "status": "error",
        "result": None,
        "message": f"写入记忆文件失败：{write_result.get('error')}"
    }
