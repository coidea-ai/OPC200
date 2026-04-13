"""Journal command: update metadata with optional retroactive template translation."""
import glob
import os
import re
from pathlib import Path

from utils.storage import build_customer_dir
from scripts.commands._meta import get_language, read_meta, write_meta


_ZH_TO_EN_REGEX = [
    (r'^# 🚀 OPC Journal \| 第 (\d+) 天章程$', r'# 🚀 OPC Journal | Day \1 Charter'),
    (r'^\*\*用户\*\*:(.*)$', r'**Customer**:\1'),
    (r'^\*\*版本\*\*:(.*)$', r'**Version**:\1'),
    (r'^## 🎯 目标$', r'## 🎯 Goals'),
    (r'^## ⚙️ 偏好设置$', r'## ⚙️ Preferences'),
    (r'^## 📝 首日仪式$', r'## 📝 Day 1 Ritual'),
    (r'^1\. 完成一件小事（哪怕只是把想法写出来）$', r'1. Do one small thing (even just write down an idea)'),
    (r'^2\. 用 `/opc-journal record "\.\.\."` 告诉我$', r'2. Run `/opc-journal record "..."`'),
    (r'^3\. 明天回来看看状态$', r'3. Check back tomorrow with status'),
    (r'^\*这不是日记本，这是你创业的飞行器黑匣子。\*$', r"*This is not a diary — it's the black box of your startup journey.*"),
    (r'^\*"放心吧，哪怕世界忘了，我也替你记着。" —— Kimi Claw\*$', r'*"Don\'t worry, even if the world forgets, I\'ll remember it for you." — Kimi Claw*'),
    (r'^## 日记条目 - (.+)$', r'## Journal Entry - \1'),
    (r'^\*\*第 (\d+) 天\*\*(.*)$', r'**Day \1**\2'),
    (r'^\*\*时间\*\*:(.*)$', r'**Time**:\1'),
    (r'^\*\*情绪\*\*:(.*)$', r'**Emotion**:\1'),
    (r'^### 内容$', r'### Content'),
    (r'^### 元数据$', r'### Metadata'),
]

_EN_TO_ZH_REGEX = [
    (r'^# 🚀 OPC Journal \| Day (\d+) Charter$', r'# 🚀 OPC Journal | 第 \1 天章程'),
    (r'^\*\*Customer\*\*:(.*)$', r'**用户**:\1'),
    (r'^\*\*Version\*\*:(.*)$', r'**版本**:\1'),
    (r'^## 🎯 Goals$', r'## 🎯 目标'),
    (r'^## ⚙️ Preferences$', r'## ⚙️ 偏好设置'),
    (r'^## 📝 Day 1 Ritual$', r'## 📝 首日仪式'),
    (r'^1\. Do one small thing \(even just write down an idea\)$', r'1. 完成一件小事（哪怕只是把想法写出来）'),
    (r'^2\. Run `/opc-journal record "\.\.\."`$', r'2. 用 `/opc-journal record "..."` 告诉我'),
    (r'^3\. Check back tomorrow with status$', r'3. 明天回来看看状态'),
    (r'^\*This is not a diary — it\'s the black box of your startup journey\.\*$', r'*这不是日记本，这是你创业的飞行器黑匣子。*'),
    (r'^\*"Don\'t worry, even if the world forgets, I\'ll remember it for you\." — Kimi Claw\*$', r'*"放心吧，哪怕世界忘了，我也替你记着。" —— Kimi Claw*'),
    (r'^## Journal Entry - (.+)$', r'## 日记条目 - \1'),
    (r'^\*\*Day (\d+)\*\*(.*)$', r'**第 \1 天**\2'),
    (r'^\*\*Time\*\*:(.*)$', r'**时间**:\1'),
    (r'^\*\*Emotion\*\*:(.*)$', r'**情绪**:\1'),
    (r'^### Content$', r'### 内容'),
    (r'^### Metadata$', r'### 元数据'),
]


def _translate_file(path: str, old_lang: str, new_lang: str) -> bool:
    if old_lang == new_lang:
        return False
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return False

    if old_lang == "zh" and new_lang == "en":
        regex_pairs = _ZH_TO_EN_REGEX
    elif old_lang == "en" and new_lang == "zh":
        regex_pairs = _EN_TO_ZH_REGEX
    else:
        return False

    lines = text.splitlines()
    new_lines = []
    changed = False
    for line in lines:
        new_line = line
        for pat, repl in regex_pairs:
            new_line, count = re.subn(pat, repl, new_line, count=1)
            if count:
                changed = True
                break
        new_lines.append(new_line)

    if not changed:
        return False

    try:
        Path(path).write_text("\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        return True
    except Exception:
        return False


def run(customer_id: str, args: dict) -> dict:
    """Update journal metadata and retroactively translate document templates if language changes."""
    meta = read_meta(customer_id)
    if not meta:
        return {
            "status": "error",
            "result": None,
            "message": "Journal not initialized. Run `/opc-journal init` first.",
        }

    old_lang = get_language(customer_id)
    new_lang = args.get("language") or old_lang
    goals = args.get("goals")
    preferences = args.get("preferences")

    updated = False
    if new_lang and new_lang != old_lang:
        meta["language"] = new_lang
        updated = True

    if goals is not None:
        meta["goals"] = goals if isinstance(goals, list) else [goals]
        updated = True

    if preferences is not None:
        meta["preferences"] = preferences if isinstance(preferences, dict) else {}
        updated = True

    if not updated:
        lang = old_lang
        msg = "Nothing to update." if lang == "en" else "没有需要更新的内容。"
        return {"status": "success", "result": {"changed": False}, "message": msg}

    write_meta(customer_id, meta)

    translated_count = 0
    if new_lang != old_lang:
        memory_dir = os.path.expanduser(os.path.join(build_customer_dir(customer_id), "memory"))
        if os.path.exists(memory_dir):
            for f in sorted(glob.glob(os.path.join(memory_dir, "*.md"))):
                if _translate_file(f, old_lang, new_lang):
                    translated_count += 1

    lang = new_lang
    if lang == "en":
        msg = f"Meta updated for {customer_id}. Language: {new_lang}."
        if translated_count:
            msg += f" Retroactively translated {translated_count} document(s)."
    else:
        msg = f"已更新 {customer_id} 的元信息。语言：{new_lang}。"
        if translated_count:
            msg += f" 已回溯翻译 {translated_count} 个文档。"

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "language": new_lang,
            "changed": True,
            "translated_documents": translated_count,
        },
        "message": msg,
    }
