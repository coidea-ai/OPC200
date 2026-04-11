"""Journal command: insights (daily/weekly)."""
import glob
import os
import re
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file
from scripts.commands.i18n import t


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
        files = glob.glob(f"{memory_dir}/*.md")
        # Sort by dd-mm-yy date ascending
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
    import os
    dated = []
    for s in sources:
        file_date = _parse_file_date(s)
        if file_date != "00-00-00":
            dated.append((file_date, s))
        else:
            # Fallback to mtime for dreams.md etc.
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


def _generate_insight(interpretation: dict, day: int, args: dict) -> dict:
    theme_scores = interpretation.get("themes", {})
    total_mentions = interpretation.get("activity_mentions", 0)
    emotions = interpretation.get("emotions", {})

    if theme_scores.get("overload", 0) >= 2 or emotions.get("疲惫", 0) >= 2:
        day_theme = t("insights.theme_overload", args)
        summary = t("insights.summary_overload", args)
        recommendations = [
            {"priority": "high", "action": "今晚给自己 1 小时完全离线的时间", "rationale": "持续高压会降低决策质量"},
            {"priority": "medium", "action": "把明天的任务清单减半", "rationale": "完成最重要的一件事，胜过做十件平庸的事"},
        ]
    elif theme_scores.get("pivot_risk", 0) >= 2:
        day_theme = t("insights.theme_pivot", args)
        summary = t("insights.summary_pivot", args)
        recommendations = [
            {"priority": "high", "action": "列出继续当前方向的 3 个证据和 3 个反证", "rationale": "结构化思考能减少情绪干扰"},
            {"priority": "medium", "action": "找 1 位潜在用户做 15 分钟快速访谈", "rationale": "外部信号比内部纠结更有价值"},
        ]
    elif theme_scores.get("momentum", 0) >= 2:
        day_theme = t("insights.theme_momentum", args)
        summary = t("insights.summary_momentum", args)
        recommendations = [
            {"priority": "high", "action": "把当前的胜利用一句话记录下来", "rationale": "里程碑需要被标记才能成为叙事的一部分"},
            {"priority": "medium", "action": "规划下一步如何把这种势头转化为可复用的流程", "rationale": "从偶发到系统，是 OPC 成长的关键"},
        ]
    elif theme_scores.get("isolation", 0) >= 2:
        day_theme = t("insights.theme_isolation", args)
        summary = t("insights.summary_isolation", args)
        recommendations = [
            {"priority": "high", "action": "在 OPC200 社区或 Discord 分享一个你最近的困惑", "rationale": "即使是简单的表达也能打破孤立感"},
            {"priority": "medium", "action": "预约一次和同行/朋友的咖啡聊天", "rationale": "创始人需要镜子"},
        ]
    elif theme_scores.get("learning", 0) >= 2:
        day_theme = t("insights.theme_learning", args)
        summary = t("insights.summary_learning", args)
        recommendations = [
            {"priority": "high", "action": "把今天学会的东西写成 3 步操作清单", "rationale": "教是最好的学"},
            {"priority": "medium", "action": "思考这个技能如何应用到下一个任务", "rationale": "知识和行动之间需要一座桥"},
        ]
    else:
        day_theme = t("insights.theme_default", args)
        summary = t("insights.summary_default", args)
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
                "theme": t("insights.journey_start", args),
                "summary": t("insights.journey_start_summary", args),
                "recommendations": [
                    {"priority": "high", "action": t("insights.rec_1_action", args), "rationale": t("insights.rec_1_rationale", args)},
                    {"priority": "medium", "action": t("insights.rec_2_action", args), "rationale": t("insights.rec_2_rationale", args)}
                ]
            },
            "message": t("insights.message_empty", args, day=day)
        }

    raw_text, dates_read = _read_recent(sources, days_back)
    themes = _detect_themes(raw_text)
    emotions = {}
    for emo in EMOTION_PATTERN.findall(raw_text):
        emotions[emo] = emotions.get(emo, 0) + 1
    activity_mentions = len([l for l in raw_text.split("\n") if l.strip() and not l.strip().startswith("#")])

    interpretation = {"themes": themes, "emotions": emotions, "activity_mentions": activity_mentions, "dates_read": dates_read}
    insight = _generate_insight(interpretation, day, args)
    insight["customer_id"] = customer_id
    insight["generated_at"] = datetime.now().isoformat()
    insight["data_source"] = "openclaw_dreams_memory"

    return {
        "status": "success",
        "result": insight,
        "message": t("insights.message_normal", args, day=day, days=len(dates_read))
    }
