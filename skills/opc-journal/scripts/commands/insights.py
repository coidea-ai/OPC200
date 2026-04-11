"""Journal command: insights (daily/weekly)."""
import glob
import os
import re
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file
from scripts.commands._meta import get_language


OPC_THEMES = {
    "pivot_risk": re.compile(r"(没效果|没 traction|方向|转型|换方向|PMF|验证失败|pivot|direction|validation failed)", re.IGNORECASE),
    "momentum": re.compile(r"(完成|发布|上线|销售|收款|签约|里程碑|突破|completed|shipped|launched|sale|milestone|breakthrough)", re.IGNORECASE),
    "overload": re.compile(r"(太多|忙不过来|焦虑|疲惫| burnout|通宵|加班|忙死了|overwhelm|burnout|exhausted|too much)", re.IGNORECASE),
    "isolation": re.compile(r"(没人|孤独|一个人|没反馈|迷茫|没思路|lonely|alone|no feedback|lost|isolated)", re.IGNORECASE),
    "learning": re.compile(r"(学会|掌握了|第一次|新技能|恍然大悟|理解|搞懂了|learned|first time|new skill|figured out|understood)", re.IGNORECASE),
}

EMOTION_PATTERN = re.compile(r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动|happy|anxious|confused|frustrated|excited|tired|satisfied|worried|relaxed|sad|nervous)")


def _find_sources(customer_id: str):
    sources = []
    base = build_customer_dir(customer_id)
    dreams = f"{base}/dreams.md"
    if os.path.exists(os.path.expanduser(dreams)):
        sources.append(dreams)
    memory_dir = f"{base}/memory"
    if os.path.exists(os.path.expanduser(memory_dir)):
        files = glob.glob(f"{memory_dir}/*.md")
        files.sort(key=lambda f: _parse_file_date(f))
        sources.extend(files)
    if not sources:
        ws = "~/.openclaw/workspace/memory"
        if os.path.exists(os.path.expanduser(ws)):
            files = glob.glob(f"{ws}/*.md")
            files.sort(key=lambda f: _parse_file_date(f))
            sources.extend(files)
    return sources


def _parse_file_date(path: str) -> str:
    basename = os.path.basename(path)
    m = re.search(r"(\d{2}-\d{2}-\d{2})\.md$", basename)
    if m:
        return m.group(1)
    return "00-00-00"


def _read_recent(sources: list, days: int = 7):
    dated = []
    for s in sources:
        file_date = _parse_file_date(s)
        if file_date != "00-00-00":
            dated.append((file_date, s))
        else:
            mtime_str = datetime.fromtimestamp(os.path.getmtime(s)).strftime("%d-%m-%y")
            dated.append((mtime_str, s))
    dated.sort(key=lambda x: datetime.strptime(x[0], "%d-%m-%y"))
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


def _generate_insight(interpretation: dict, day: int, lang: str) -> dict:
    theme_scores = interpretation.get("themes", {})
    total_mentions = interpretation.get("activity_mentions", 0)
    emotions = interpretation.get("emotions", {})
    is_en = lang == "en"

    if theme_scores.get("overload", 0) >= 2 or emotions.get("疲惫", 0) >= 2 or emotions.get("tired", 0) >= 2:
        day_theme = "Watch Your Pace" if is_en else "注意节奏"
        summary = "High-intensity work signals detected this week. Consider sustainability." if is_en else "本周记录了高强度工作信号，建议关注可持续性。"
        recommendations = [
            {"priority": "high", "action": "今晚给自己 1 小时完全离线的时间" if not is_en else "Take 1 hour fully offline tonight", "rationale": "持续高压会降低决策质量" if not is_en else "Sustained pressure degrades decision quality"},
            {"priority": "medium", "action": "把明天的任务清单减半" if not is_en else "Halve tomorrow's task list", "rationale": "完成最重要的一件事，胜过做十件平庸的事" if not is_en else "One important thing done beats ten mediocre ones"},
        ]
    elif theme_scores.get("pivot_risk", 0) >= 2:
        day_theme = "Strategic Reflection" if is_en else "战略反思期"
        summary = "Repeated validation feedback suggests revisiting your current direction." if is_en else "连续的验证反馈提示可能需要重新审视当前方向。"
        recommendations = [
            {"priority": "high", "action": "列出继续当前方向的 3 个证据和 3 个反证" if not is_en else "List 3 pieces of evidence for and against your current direction", "rationale": "结构化思考能减少情绪干扰" if not is_en else "Structured thinking reduces emotional noise"},
            {"priority": "medium", "action": "找 1 位潜在用户做 15 分钟快速访谈" if not is_en else "Do a 15-minute quick interview with 1 potential user", "rationale": "外部信号比内部纠结更有价值" if not is_en else "External signals are more valuable than internal debates"},
        ]
    elif theme_scores.get("momentum", 0) >= 2:
        day_theme = "Momentum Building" if is_en else "势能上升"
        summary = "Clear forward signals this week — momentum is building." if is_en else "本周有明确的推进信号，势能正在积累。"
        recommendations = [
            {"priority": "high", "action": "把当前的胜利用一句话记录下来" if not is_en else "Write down the current win in one sentence", "rationale": "里程碑需要被标记才能成为叙事的一部分" if not is_en else "Milestones must be marked to become part of the narrative"},
            {"priority": "medium", "action": "规划下一步如何把这种势头转化为可复用的流程" if not is_en else "Plan how to turn this momentum into a repeatable process", "rationale": "从偶发到系统，是 OPC 成长的关键" if not is_en else "From sporadic to systematic is key to OPC growth"},
        ]
    elif theme_scores.get("isolation", 0) >= 2:
        day_theme = "Need Connection" if is_en else "连接需求"
        summary = "Signals suggest you're carrying too much alone. Reach out." if is_en else "信号显示你可能在独自承担太多，需要外部连接。"
        recommendations = [
            {"priority": "high", "action": "在 OPC200 社区或 Discord 分享一个你最近的困惑" if not is_en else "Share a recent confusion in the OPC200 community or Discord", "rationale": "即使是简单的表达也能打破孤立感" if not is_en else "Even simple expression can break isolation"},
            {"priority": "medium", "action": "预约一次和同行/朋友的咖啡聊天" if not is_en else "Schedule a coffee chat with a peer or friend", "rationale": "创始人需要镜子" if not is_en else "Founders need mirrors"},
        ]
    elif theme_scores.get("learning", 0) >= 2:
        day_theme = "Rapid Growth" if is_en else "快速成长"
        summary = "Strong learning curve this week — new skills are internalizing." if is_en else "本周显示出强烈的学习曲线，新技能正在内化。"
        recommendations = [
            {"priority": "high", "action": "把今天学会的东西写成 3 步操作清单" if not is_en else "Write what you learned today into a 3-step checklist", "rationale": "教是最好的学" if not is_en else "Teaching is the best learning"},
            {"priority": "medium", "action": "思考这个技能如何应用到下一个任务" if not is_en else "Think about how this skill applies to the next task", "rationale": "知识和行动之间需要一座桥" if not is_en else "Knowledge and action need a bridge"},
        ]
    else:
        day_theme = "Steady Accumulation" if is_en else "持续积累"
        summary = "This period shows steady progress without strong signals." if is_en else "今天/本周的记忆显示平稳推进，没有特别强烈的信号。"
        recommendations = [
            {"priority": "medium", "action": "回顾最近 7 天的目标，确认首要任务仍然正确" if not is_en else "Review the goals of the last 7 days to confirm the top priority is still right", "rationale": "平稳期最容易偏离主线" if not is_en else "Stable periods are when it's easiest to drift off course"},
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
    lang = get_language(customer_id)
    is_en = lang == "en"
    sources = _find_sources(customer_id)

    if not sources:
        return {
            "status": "success",
            "result": {
                "day": day,
                "customer_id": customer_id,
                "theme": "Journey Begins" if is_en else "旅程开始",
                "summary": "Every great story begins with a single sentence. Today's note will be the first marker you look back on." if is_en else "所有的宏大故事都始于一个短句。你今天的记录，会成为未来回望时的第一块路标。",
                "recommendations": [
                    {"priority": "high", "action": "记录一件今天完成的、再小也算数的事" if not is_en else "Record one small thing you achieved today — it counts", "rationale": "第一天的仪式不是宏大叙事，而是证明自己来了" if not is_en else "Day 1 ritual is about showing up, not grand narratives"},
                    {"priority": "medium", "action": "写下一个你最想在 30 天后看到的变化" if not is_en else "Write down one change you'd love to see in 30 days", "rationale": "让未来的自己有东西可对比" if not is_en else "Give your future self something to compare against"}
                ]
            },
            "message": f"Day {day} insight — every journey starts with a blank page." if is_en else f"第 {day} 天洞察——每一段旅程都从一张白纸开始。"
        }

    raw_text, dates_read = _read_recent(sources, days_back)
    themes = _detect_themes(raw_text)
    emotions = {}
    for emo in EMOTION_PATTERN.findall(raw_text):
        emotions[emo] = emotions.get(emo, 0) + 1
    activity_mentions = len([l for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")])

    interpretation = {"themes": themes, "emotions": emotions, "activity_mentions": activity_mentions, "dates_read": dates_read}
    insight = _generate_insight(interpretation, day, lang)
    insight["customer_id"] = customer_id
    insight["generated_at"] = datetime.now().isoformat()
    insight["data_source"] = "openclaw_dreams_memory"

    msg = f"Insight generated for Day {day} from the last {len(dates_read)} day(s)." if is_en else f"已为第 {day} 天生成洞察，基于最近 {len(dates_read)} 天的记录。"
    return {
        "status": "success",
        "result": insight,
        "message": msg
    }
