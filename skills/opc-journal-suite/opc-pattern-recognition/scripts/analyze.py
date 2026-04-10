"""opc-pattern-recognition analyze module (v2.4-refactored).

v2.4 Change: No longer performs its own raw analysis.
Instead, reads OpenClaw dreaming output (dreams.md / memory/*.md)
and performs OPC-specific interpretation.
"""
import json
import os
import re
import glob
from datetime import datetime
from collections import Counter

# Add parent directory to path for utils import (local test compatibility)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.storage import read_memory_file, build_customer_dir


# Regex patterns for OPC-specific interpretation from natural language memories
OPC_SIGNALS = {
    "work_hours": re.compile(r"(\d{1,2}):(\d{2})|上午|下午|晚上|凌晨|早晨", re.IGNORECASE),
    "emotions": re.compile(r"(开心|焦虑|困惑|沮丧|兴奋|疲惫|满足|担心|紧张|放松|失落|激动)", re.IGNORECASE),
    "decisions": re.compile(r"(决定|选择|放弃|切换|采用|改用|定下来|拍板|纠结|犹豫)(.*?)(?:。|；|;|\n)", re.IGNORECASE),
    "milestones": re.compile(r"(完成|发布|上线|销售|签约|收款|MVP|原型|第一笔|第一个|突破|里程碑)", re.IGNORECASE),
    "help_seeking": re.compile(r"(问|请教|讨论|委托|让.*帮忙|找.*解决|求助)", re.IGNORECASE),
    "blockers": re.compile(r"(卡|卡住|阻塞|瓶颈|搞不定|没思路|失败|报错|bug|问题)(.*?)(?:。|；|;|\n)", re.IGNORECASE),
}


def _find_dreams_source(customer_id: str) -> list:
    """Find available memory/dreams sources for customer.
    Priority: dreams.md > memory/*.md > workspace memory (fallback)
    """
    sources = []
    base = os.path.expanduser(build_customer_dir(customer_id))
    dreams_path = os.path.join(base, "dreams.md")
    if os.path.exists(dreams_path):
        sources.append(dreams_path)

    memory_dir = os.path.join(base, "memory")
    if os.path.exists(memory_dir):
        files = sorted(glob.glob(os.path.join(memory_dir, "*.md")))
        sources.extend(files)

    # Fallback: workspace-level memory (development/testing)
    if not sources:
        ws_memory = os.path.expanduser("~/.openclaw/workspace/memory")
        if os.path.exists(ws_memory):
            files = sorted(glob.glob(os.path.join(ws_memory, "*.md")))
            sources.extend(files)

    return sources


def _read_sources(sources: list) -> str:
    """Read and concatenate source files."""
    contents = []
    for path in sources:
        result = read_memory_file(path)
        if result.get("success"):
            contents.append(f"\n--- FILE: {path} ---\n{result['content']}")
    return "\n".join(contents)


def _extract_signals(text: str) -> dict:
    """Extract OPC-relevant signals from raw memory text."""
    signals = {
        "emotions": [],
        "decisions": [],
        "milestones": [],
        "help_seeking_count": 0,
        "blockers": [],
        "hours_mentions": [],
        "daily_activity_lines": [line for line in text.split("\n") if line.strip() and not line.strip().startswith("#")],
    }

    for emotion in OPC_SIGNALS["emotions"].findall(text):
        signals["emotions"].append(emotion)

    for match in OPC_SIGNALS["decisions"].finditer(text):
        decision_text = match.group(0).strip()
        if len(decision_text) > 3:
            signals["decisions"].append(decision_text)

    for match in OPC_SIGNALS["milestones"].finditer(text):
        # Get surrounding context (±30 chars)
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        signals["milestones"].append(text[start:end].strip().replace("\n", " "))

    signals["help_seeking_count"] = len(OPC_SIGNALS["help_seeking"].findall(text))

    for match in OPC_SIGNALS["blockers"].finditer(text):
        blocker_text = match.group(0).strip()
        if len(blocker_text) > 3:
            signals["blockers"].append(blocker_text)

    for match in OPC_SIGNALS["work_hours"].finditer(text):
        signals["hours_mentions"].append(match.group(0))

    return signals


def _interpret_patterns(signals: dict, days_span: int = 7) -> dict:
    """Transform raw signals into OPC-specific interpretations."""
    emotion_counter = Counter(signals["emotions"])
    decision_counter = Counter(signals["decisions"])
    blocker_counter = Counter(signals["blockers"])

    # Work rhythm interpretation
    activity_count = len(signals["daily_activity_lines"])
    avg_daily_activity = round(activity_count / max(days_span, 1), 1)

    # Emotional pattern
    dominant_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else "neutral"
    emotional_volatility = len(emotion_counter)  # more types = higher volatility

    # Decision style
    decision_texts = signals["decisions"]
    hesitation_keywords = ["纠结", "犹豫", "没想好", "待定"]
    hesitation_count = sum(1 for d in decision_texts for kw in hesitation_keywords if kw in d)
    risk_keywords = ["放弃", "切换", "all in", "赌", "冒险"]
    risk_count = sum(1 for d in decision_texts for kw in risk_keywords if kw in d)

    if hesitation_count > len(decision_texts) * 0.3:
        decision_style = "谨慎型 (Conservative)"
    elif risk_count > len(decision_texts) * 0.2:
        decision_style = "进取型 (Aggressive)"
    else:
        decision_style = "平衡型 (Balanced)"

    # Help-seeking pattern
    if signals["help_seeking_count"] == 0:
        help_pattern = "高度独立，较少主动求助"
    elif signals["help_seeking_count"] <= 3:
        help_pattern = "适度协作，遇到瓶颈时求助"
    else:
        help_pattern = "频繁协作，善于利用外部支持"

    # Milestone velocity
    milestone_count = len(signals["milestones"])
    milestone_velocity = "高" if milestone_count >= days_span * 0.5 else "中" if milestone_count > 0 else "低"

    # Blocker pattern
    recurring_themes = [item[0] for item in blocker_counter.most_common(3)]

    return {
        "work_rhythm": {
            "days_analyzed": days_span,
            "total_activity_mentions": activity_count,
            "avg_daily_mentions": avg_daily_activity,
            "interpretation": "活跃" if avg_daily_activity >= 3 else "中等" if avg_daily_activity >= 1 else "较低"
        },
        "emotional_pattern": {
            "dominant_emotion": dominant_emotion,
            "emotional_volatility": emotional_volatility,
            "emotion_distribution": dict(emotion_counter.most_common(5)),
            "interpretation": (
                "情绪起伏较大" if emotional_volatility >= 4
                else "情绪相对稳定" if emotional_volatility <= 2
                else "情绪有波动但可控"
            )
        },
        "decision_style": {
            "style_label": decision_style,
            "total_decisions_logged": len(decision_texts),
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
            "velocity_label": milestone_velocity,
            "recent_milestone_signals": signals["milestones"][:3]
        },
        "blocker_themes": {
            "recurring_blockers": recurring_themes,
            "total_blocker_mentions": sum(blocker_counter.values())
        }
    }


def main(context: dict) -> dict:
    """Analyze patterns by interpreting OpenClaw dreaming output."""
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})

        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }

        days = input_data.get("days", 7)
        analysis_type = input_data.get("type", "general")

        sources = _find_dreams_source(customer_id)
        if not sources:
            return {
                "status": "success",
                "result": {
                    "customer_id": customer_id,
                    "analysis_type": analysis_type,
                    "interpretation": None,
                    "note": "No dreams.md or memory files found for this customer yet. Interpretation will improve as journal entries accumulate."
                },
                "message": "No memory sources available yet"
            }

        raw_text = _read_sources(sources[-min(days * 2, len(sources)):])  # read recent files
        signals = _extract_signals(raw_text)
        interpretation = _interpret_patterns(signals, days)

        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "analysis_type": analysis_type,
                "data_source": "openclaw_dreams_memory",
                "files_read": len(sources),
                "interpretation": interpretation
            },
            "message": f"Interpreted patterns for {customer_id} from {len(sources)} memory source(s)"
        }

    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Pattern interpretation failed: {str(e)}"
        }


if __name__ == "__main__":
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "days": 7,
            "type": "weekly"
        }
    }
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
