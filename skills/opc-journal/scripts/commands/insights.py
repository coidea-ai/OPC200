"""Journal command: insights (daily/weekly)."""
import glob
import re
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file


OPC_THEMES = {
    "pivot_risk": re.compile(r"(没效果|没 traction|方向|转型|换方向|PMF|验证失败)", re.IGNORECASE),
    "momentum": re.compile(r"(完成|发布|上线|销售|收款|签约|里程碑|突破)", re.IGNORECASE),
    "overload": re.compile(r"(太多|忙不过来|焦虑|疲惫| burnout|通宵|加班|忙死了)", re.IGNORECASE),
    "isolation": re.compile(r"(没人|孤独|一个人|没反馈|迷茫|没思路)", re.IGNORECASE),
    "learning": re.compile(r"(学会|掌握了|第一次|新技能|恍然大悟|理解|搞懂了)", re.IGNORECASE),
}

EMOTION_PATTERN = re.compile(r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动)")


def _find_sources(customer_id: str):
    import os
    sources = []
    base = build_customer_dir(customer_id)
    dreams = f"{base}/dreams.md"
    if os.path.exists(os.path.expanduser(dreams)):
        sources.append(dreams)
    memory_dir = f"{base}/memory"
    if os.path.exists(os.path.expanduser(memory_dir)):
        sources.extend(sorted(glob.glob(f"{memory_dir}/*.md")))
    if not sources:
        ws = "~/.openclaw/workspace/memory"
        if os.path.exists(os.path.expanduser(ws)):
            sources.extend(sorted(glob.glob(f"{ws}/*.md")))
    return sources


def _read_recent(sources: list, days: int = 7):
    import os
    dated = []
    for s in sources:
        basename = os.path.basename(s)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
        file_date = m.group(1) if m else datetime.fromtimestamp(os.path.getmtime(s)).strftime("%Y-%m-%d")
        dated.append((file_date, s))
    dated.sort(key=lambda x: x[0])
    recent = dated[-min(days, len(dated)):]
    contents = []
    dates_read = []
    for d, path in recent:
        res = read_memory_file(path)
        if res.get("success"):
            contents.append(res["content"])
            dates_read.append(d)
    return "\n\n".join(contents), dates_read


def _detect_themes(text: str) -> dict:
    return {name: len(p.findall(text)) for name, p in OPC_THEMES.items()}


def _generate_insight(interpretation: dict, day: int) -> dict:
    theme_scores = interpretation.get("themes", {})
    total_mentions = interpretation.get("activity_mentions", 0)
    emotions = interpretation.get("emotions", {})

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


def run(customer_id: str, args: dict) -> dict:
    day = args.get("day", 1)
    days_back = args.get("days_back", 7)
    sources = _find_sources(customer_id)

    if not sources:
        return {
            "status": "success",
            "result": {
                "day": day,
                "customer_id": customer_id,
                "theme": "旅程开始",
                "summary": "所有的 long story 都始于一个短句。你今天的记录，会成为未来回望时的第一块路标。",
                "recommendations": [
                    {"priority": "high", "action": "记录一件今天完成的、再小也算数的事", "rationale": "Day 1 的 ritual 不是宏大叙事，而是证明自己来了"},
                    {"priority": "medium", "action": "写下一个你最想在 30 天后看到的变化", "rationale": "让未来的自己有东西可对比"}
                ]
            },
            "message": f"Daily insight for Day {day} — every journey starts with a blank page."
        }

    raw_text, dates_read = _read_recent(sources, days_back)
    themes = _detect_themes(raw_text)
    emotions = {}
    for emo in EMOTION_PATTERN.findall(raw_text):
        emotions[emo] = emotions.get(emo, 0) + 1
    activity_mentions = len([l for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")])

    interpretation = {"themes": themes, "emotions": emotions, "activity_mentions": activity_mentions, "dates_read": dates_read}
    insight = _generate_insight(interpretation, day)
    insight["customer_id"] = customer_id
    insight["generated_at"] = datetime.now().isoformat()
    insight["data_source"] = "openclaw_dreams_memory"

    return {
        "status": "success",
        "result": insight,
        "message": f"Insight generated for Day {day} from {len(dates_read)} day(s)"
    }
