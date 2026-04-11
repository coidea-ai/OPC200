"""Journal command: analyze (pattern interpretation layer v2.4)."""
import glob
import os
import re
from collections import Counter
from datetime import datetime

from utils.storage import build_customer_dir, read_memory_file
from scripts.commands._meta import get_language


OPC_SIGNALS = {
    "work_hours": re.compile(r"(\d{1,2}):(\d{2})|上午|下午|晚上|凌晨|早晨|morning|afternoon|evening|night", re.IGNORECASE),
    "emotions": re.compile(r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动|happy|anxious|confused|frustrated|excited|tired|relaxed|sad|nervous)", re.IGNORECASE),
    "decisions": re.compile(r"(决定|选择|放弃|切换|采用|改用|定下来|拍板|纠结|犹豫|decided|choose|switch|adopt|finalize|hesitate)(.*?)(?:。|；|;|\n|\.)", re.IGNORECASE),
    "milestones": re.compile(r"(完成|发布|上线|销售|签约|收款|MVP|原型|第一笔|第一个|突破|里程碑|completed|launched|shipped|sale|signed|revenue|MVP|prototype|milestone|breakthrough)", re.IGNORECASE),
    "help_seeking": re.compile(r"(问|请教|讨论|委托|让.*帮忙|找.*解决|求助|ask|discuss|delegate|help)", re.IGNORECASE),
    "blockers": re.compile(r"(卡|卡住|阻塞|瓶颈|搞不定|没思路|失败|报错|bug|问题|stuck|blocked|bottleneck|failed|error|bug|issue)(.*?)(?:。|；|;|\n|\.)", re.IGNORECASE),
}


def _parse_file_date(path: str) -> str:
    basename = os.path.basename(path)
    m = re.search(r"(\d{2}-\d{2}-\d{2})\.md$", basename)
    if m:
        return m.group(1)
    return "00-00-00"


def _find_sources(customer_id: str):
    sources = []
    base = build_customer_dir(customer_id)
    dreams = f"{base}/dreams.md"
    if os.path.exists(os.path.expanduser(dreams)):
        sources.append(dreams)
    memory_dir = f"{base}/memory"
    if os.path.exists(os.path.expanduser(memory_dir)):
        files = glob.glob(f"{memory_dir}/*.md")
        files.sort(key=lambda f: datetime.strptime(_parse_file_date(f), "%d-%m-%y"))
        sources.extend(files)
    if not sources:
        ws = "~/.openclaw/workspace/memory"
        if os.path.exists(os.path.expanduser(ws)):
            files = glob.glob(f"{ws}/*.md")
            files.sort(key=lambda f: datetime.strptime(_parse_file_date(f), "%d-%m-%y"))
            sources.extend(files)
    return sources


def _extract_signals(text: str) -> dict:
    return {
        "emotions": OPC_SIGNALS["emotions"].findall(text),
        "decisions": [m.group(0).strip() for m in OPC_SIGNALS["decisions"].finditer(text) if len(m.group(0).strip()) > 3],
        "milestones": [text[max(0, m.start()-30):min(len(text), m.end()+30)].strip().replace("\n", " ") for m in OPC_SIGNALS["milestones"].finditer(text)],
        "help_seeking_count": len(OPC_SIGNALS["help_seeking"].findall(text)),
        "blockers": [m.group(0).strip() for m in OPC_SIGNALS["blockers"].finditer(text) if len(m.group(0).strip()) > 3],
        "hours_mentions": [m.group(0) for m in OPC_SIGNALS["work_hours"].finditer(text)],
        "daily_activity_lines": [l for l in text.split("\n") if l.strip() and not l.strip().startswith("#")],
    }


def _interpret(signals: dict, days_span: int, lang: str) -> dict:
    emotion_counter = Counter(signals["emotions"])
    decision_counter = Counter(signals["decisions"])
    blocker_counter = Counter(signals["blockers"])
    activity_count = len(signals["daily_activity_lines"])
    avg_daily = round(activity_count / max(days_span, 1), 1)
    dominant = emotion_counter.most_common(1)[0][0] if emotion_counter else ("平静" if lang != "en" else "calm")
    volatility = len(emotion_counter)

    hesitation_keywords = ["纠结", "犹豫", "没想好", "待定", "hesitate", "undecided", "uncertain"]
    risk_keywords = ["放弃", "切换", "all in", "赌", "冒险", "give up", "all in", "bet"]
    hesitation_count = sum(1 for d in signals["decisions"] for kw in hesitation_keywords if kw in d)
    risk_count = sum(1 for d in signals["decisions"] for kw in risk_keywords if kw in d)

    if lang == "en":
        if hesitation_count > len(signals["decisions"]) * 0.3:
            decision_style = "Conservative"
        elif risk_count > len(signals["decisions"]) * 0.2:
            decision_style = "Aggressive"
        else:
            decision_style = "Balanced"
    else:
        if hesitation_count > len(signals["decisions"]) * 0.3:
            decision_style = "谨慎型"
        elif risk_count > len(signals["decisions"]) * 0.2:
            decision_style = "进取型"
        else:
            decision_style = "平衡型"

    if signals["help_seeking_count"] == 0:
        help_pattern = "Highly independent, rarely seeks help" if lang == "en" else "高度独立，较少主动求助"
    elif signals["help_seeking_count"] <= 3:
        help_pattern = "Moderately collaborative, asks for help at blockers" if lang == "en" else "适度协作，遇到瓶颈时求助"
    else:
        help_pattern = "Frequently collaborative, leverages external support" if lang == "en" else "频繁协作，善于利用外部支持"

    milestone_count = len(signals["milestones"])
    if milestone_count >= days_span * 0.5:
        velocity = "High" if lang == "en" else "高"
    elif milestone_count > 0:
        velocity = "Medium" if lang == "en" else "中"
    else:
        velocity = "Low" if lang == "en" else "低"

    if avg_daily >= 3:
        rhythm_label = "Active" if lang == "en" else "活跃"
    elif avg_daily >= 1:
        rhythm_label = "Moderate" if lang == "en" else "中等"
    else:
        rhythm_label = "Low" if lang == "en" else "较低"

    if volatility >= 4:
        emotion_interp = "High emotional volatility" if lang == "en" else "情绪起伏较大"
    elif volatility <= 2:
        emotion_interp = "Emotionally stable" if lang == "en" else "情绪相对稳定"
    else:
        emotion_interp = "Emotional fluctuations, but manageable" if lang == "en" else "情绪有波动但可控"

    return {
        "work_rhythm": {
            "days_analyzed": days_span,
            "total_activity_mentions": activity_count,
            "avg_daily_mentions": avg_daily,
            "interpretation": rhythm_label
        },
        "emotional_pattern": {
            "dominant_emotion": dominant,
            "emotional_volatility": volatility,
            "emotion_distribution": dict(emotion_counter.most_common(5)),
            "interpretation": emotion_interp
        },
        "decision_style": {
            "style_label": decision_style,
            "total_decisions_logged": len(signals["decisions"]),
            "hesitation_signals": hesitation_count,
            "risk_signals": risk_count,
            "recent_decisions": list(decision_counter.keys())[:3]
        },
        "collaboration_pattern": {
            "help_seeking_frequency": signals["help_seeking_count"],
            "pattern_summary": help_pattern
        },
        "milestone_velocity": {
            "count": milestone_count,
            "velocity_label": velocity,
            "recent_milestone_signals": signals["milestones"][:3]
        },
        "blocker_themes": {
            "recurring_blockers": [item[0] for item in blocker_counter.most_common(3)],
            "total_blocker_mentions": sum(blocker_counter.values())
        }
    }


def run(customer_id: str, args: dict) -> dict:
    days = args.get("days", 7)
    lang = get_language(customer_id)
    sources = _find_sources(customer_id)
    if not sources:
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "analysis_type": args.get("dimension", "general"),
                "interpretation": None,
                "note": "No dreams.md or memory files found yet." if lang == "en" else "尚未找到 dreams.md 或 memory 文件。"
            },
            "message": "No memory sources available" if lang == "en" else "没有可用的记忆源"
        }

    texts = []
    for path in sources[-min(days * 2, len(sources)):]:
        res = read_memory_file(path)
        if res.get("success"):
            texts.append(res["content"])

    signals = _extract_signals("\n".join(texts))
    interpretation = _interpret(signals, days, lang)

    msg = f"Pattern analysis complete for {customer_id}" if lang == "en" else f"已为 {customer_id} 完成模式分析"
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "analysis_type": args.get("dimension", "general"),
            "data_source": "openclaw_dreams_memory",
            "files_read": len(sources),
            "interpretation": interpretation
        },
        "message": msg
    }
