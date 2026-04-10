"""opc-insight-generator daily summary module (v2.4-refactored).

v2.4 Change: No longer generates generic summaries.
Instead, reads OpenClaw dreaming output and produces OPC-specific insights.
"""
import json
import os
import glob
import re
from datetime import datetime, timedelta

# Add parent directory to path for utils import (local test compatibility)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.storage import read_memory_file, build_customer_dir

# OPC-relevant insight templates
OPC_THEMES = {
    "pivot_risk": re.compile(r"(没效果|没 traction|方向|转型|换方向|PMF|验证失败)", re.IGNORECASE),
    "momentum": re.compile(r"(完成|发布|上线|销售|收款|签约|里程碑|突破)", re.IGNORECASE),
    "overload": re.compile(r"(太多|忙不过来|焦虑|疲惫| burnout|通宵|加班|忙死了)", re.IGNORECASE),
    "isolation": re.compile(r"(没人|孤独|一个人|没反馈|迷茫|没思路)", re.IGNORECASE),
    "learning": re.compile(r"(学会|掌握了|第一次|新技能|恍然大悟|理解|搞懂了)", re.IGNORECASE),
}


def _find_memory_sources(customer_id: str) -> list:
    """Find memory/dreams files for customer."""
    sources = []
    base = os.path.expanduser(build_customer_dir(customer_id))
    dreams_path = os.path.join(base, "dreams.md")
    if os.path.exists(dreams_path):
        sources.append(dreams_path)

    memory_dir = os.path.join(base, "memory")
    if os.path.exists(memory_dir):
        files = sorted(glob.glob(os.path.join(memory_dir, "*.md")))
        sources.extend(files)

    if not sources:
        ws_memory = os.path.expanduser("~/.openclaw/workspace/memory")
        if os.path.exists(ws_memory):
            files = sorted(glob.glob(os.path.join(ws_memory, "*.md")))
            sources.extend(files)

    return sources


def _read_recent_sources(sources: list, days: int = 7) -> tuple:
    """Read most recent N files and return text + list of dates."""
    # Sort by filename date if possible, otherwise mtime
    dated_sources = []
    for s in sources:
        basename = os.path.basename(s)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
        if date_match:
            file_date = date_match.group(1)
        else:
            file_date = datetime.fromtimestamp(os.path.getmtime(s)).strftime("%Y-%m-%d")
        dated_sources.append((file_date, s))

    dated_sources.sort(key=lambda x: x[0])
    recent = dated_sources[-min(days, len(dated_sources)):]

    contents = []
    dates_read = []
    for d, path in recent:
        res = read_memory_file(path)
        if res.get("success"):
            contents.append(res["content"])
            dates_read.append(d)

    return "\n\n".join(contents), dates_read


def _detect_themes(text: str) -> dict:
    """Detect OPC business themes from memory text."""
    themes = {}
    for theme_name, pattern in OPC_THEMES.items():
        matches = pattern.findall(text)
        themes[theme_name] = len(matches)
    return themes


def _generate_insight(interpretation: dict, day: int) -> dict:
    """Generate OPC-specific daily insight based on interpreted memory."""
    theme_scores = interpretation.get("themes", {})
    total_mentions = interpretation.get("activity_mentions", 0)
    emotions = interpretation.get("emotions", {})

    dominant_theme = max(theme_scores, key=theme_scores.get) if theme_scores else "neutral"
    theme_score = theme_scores.get(dominant_theme, 0)

    # Determine day theme
    if theme_scores.get("overload", 0) >= 2 or emotions.get("疲惫", 0) >= 2:
        day_theme = "注意节奏"
        summary = "本周记录了高强度工作信号，建议关注可持续性。"
        recommendations = [
            {"priority": "high", "action": "今晚给自己 1 小时完全离线的时间", "rationale": "持续高压会降低决策质量"},
            {"priority": "medium", "action": "把明天的任务清单减半", "rationale": "完成最重要的一件事 > 做十件平庸的事"},
        ]
    elif theme_scores.get("pivot_risk", 0) >= 2:
        day_theme = "战略反思期"
        summary = "连续的验证反馈提示可能需要重新审视当前方向。"
        recommendations = [
            {"priority": "high", "action": "列出继续当前方向的 3 个证据和 3 个反证", "rationale": "结构化思考能减少情绪干扰"},
            {"priority": "medium", "action": "找 1 位潜在用户做 15 分钟快速访谈", "rationale": "外部信号比内部纠结更有价值"},
        ]
    elif theme_scores.get("momentum", 0) >= 2:
        day_theme = "势能上升"
        summary = "本周有明确的推进信号， momentum 正在积累。"
        recommendations = [
            {"priority": "high", "action": "把当前的胜利用一句话记录下来", "rationale": "里程碑需要被标记才能成为 narrative"},
            {"priority": "medium", "action": "规划下一步如何把这种势头转化为可复用的流程", "rationale": "从偶发到系统，是 OPC 成长的关键"},
        ]
    elif theme_scores.get("isolation", 0) >= 2:
        day_theme = "连接需求"
        summary = "信号显示你可能在独自承担太多，需要外部连接。"
        recommendations = [
            {"priority": "high", "action": "在 OPC200 社区或 Discord 分享一个你最近的困惑", "rationale": "即使是简单的表达也能打破孤立感"},
            {"priority": "medium", "action": "预约一次和同行/朋友的咖啡聊天", "rationale": "创始人需要镜子"},
        ]
    elif theme_scores.get("learning", 0) >= 2:
        day_theme = "快速成长"
        summary = "本周显示出强烈的学习曲线，新技能正在内化。"
        recommendations = [
            {"priority": "high", "action": "把今天学会的东西写成 3 步操作清单", "rationale": "教是最好的学"},
            {"priority": "medium", "action": "思考这个技能如何应用到下一个任务", "rationale": "知识和行动之间需要一座桥"},
        ]
    else:
        day_theme = "持续积累"
        summary = "今天/本周的记忆显示平稳推进，没有特别强烈的信号。"
        recommendations = [
            {"priority": "medium", "action": "回顾最近 7 天的目标，确认首要任务仍然正确", "rationale": "平稳期最容易偏离主线"},
        ]

    return {
        "day": day,
        "theme": day_theme,
        "summary": summary,
        "recommendations": recommendations,
        "detected_signals": {
            "themes": theme_scores,
            "emotions": emotions,
            "activity_mentions": total_mentions
        }
    }


def main(context: dict) -> dict:
    """Generate daily insight from OpenClaw dreaming output."""
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})

        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }

        day = input_data.get("day", 1)
        days_back = input_data.get("days_back", 7)

        sources = _find_memory_sources(customer_id)
        if not sources:
            return {
                "status": "success",
                "result": {
                    "day": day,
                    "customer_id": customer_id,
                    "theme": "旅程开始",
                    "summary": "还没有足够的记忆来生成洞察。继续记录，我会越来越懂你。",
                    "recommendations": [
                        {"priority": "high", "action": "今天完成一件小事并告诉我", "rationale": "Journal 的价值来自连续性"}
                    ]
                },
                "message": f"Daily insight prepared for Day {day} (insufficient memory yet)"
            }

        raw_text, dates_read = _read_recent_sources(sources, days_back)
        themes = _detect_themes(raw_text)

        # Simple emotion extraction (re-use pattern recognition signals)
        emotion_pattern = re.compile(r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动)")
        emotions = {}
        for emo in emotion_pattern.findall(raw_text):
            emotions[emo] = emotions.get(emo, 0) + 1

        activity_mentions = len([l for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")])

        interpretation = {
            "themes": themes,
            "emotions": emotions,
            "activity_mentions": activity_mentions,
            "dates_read": dates_read
        }

        insight = _generate_insight(interpretation, day)
        insight["customer_id"] = customer_id
        insight["generated_at"] = datetime.now().isoformat()
        insight["data_source"] = "openclaw_dreams_memory"

        return {
            "status": "success",
            "result": insight,
            "message": f"Daily insight generated for Day {day} from {len(dates_read)} memory day(s)"
        }

    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Daily insight generation failed: {str(e)}"
        }


if __name__ == "__main__":
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "day": 7,
            "days_back": 7
        }
    }
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
