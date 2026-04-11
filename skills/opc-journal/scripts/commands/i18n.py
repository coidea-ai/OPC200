"""Minimal i18n helper for opc-journal commands."""

DEFAULT_LANG = "zh"


TEXTS = {
    "init": {
        "charter_title": {
            "zh": "第 {day} 天章程",
            "en": "Day {day} Charter",
        },
        "manifesto_subtitle": {
            "zh": "用户",
            "en": "Customer",
        },
        "version_label": {
            "zh": "版本",
            "en": "Version",
        },
        "goals_title": {
            "zh": "目标",
            "en": "Goals",
        },
        "preferences_title": {
            "zh": "偏好设置",
            "en": "Preferences",
        },
        "ritual_title": {
            "zh": "首日仪式",
            "en": "Day 1 Ritual",
        },
        "ritual_steps": {
            "zh": "1. 完成一件小事（哪怕只是把想法写出来）\n2. 用 `/opc-journal record \"...\"` 告诉我\n3. 明天回来看看状态",
            "en": "1. Do one small thing (even just write down an idea)\n2. Run `/opc-journal record \"...\"`\n3. Check back tomorrow with status",
        },
        "footer_note": {
            "zh": "这不是日记本，这是你创业的飞行器黑匣子。",
            "en": "This is not a diary — it's the black box of your startup journey.",
        },
        "success_message": {
            "zh": "🎉 {customer_id} 的 Journal 已初始化。第 {day} 天正式开始。试试：/opc-journal record \"你的第一步\"",
            "en": "🎉 Journal initialized for {customer_id}. Day {day} begins now. Try: /opc-journal record \"Your first step\"",
        },
        "error_message": {
            "zh": "写入记忆文件失败：{error}",
            "en": "Failed to write memory: {error}",
        },
    },
    "record": {
        "entry_title": {
            "zh": "日记条目",
            "en": "Journal Entry",
        },
        "day_label": {
            "zh": "第 {day} 天",
            "en": "Day {day}",
        },
        "time_label": {
            "zh": "时间",
            "en": "Time",
        },
        "emotion_label": {
            "zh": "情绪",
            "en": "Emotion",
        },
        "content_label": {
            "zh": "内容",
            "en": "Content",
        },
        "metadata_label": {
            "zh": "元数据",
            "en": "Metadata",
        },
        "missing_content": {
            "zh": "请提供记录内容（content 字段不能为空）",
            "en": "content is required",
        },
        "success_first": {
            "zh": "🎉 已记录条目 {entry_id}——这是你的第一条真实记录。第 {day} 天正式启程。",
            "en": "🎉 Entry {entry_id} recorded — that's your first real entry. Day {day} is officially in motion.",
        },
        "success_normal": {
            "zh": "已记录条目 {entry_id}",
            "en": "Entry {entry_id} recorded",
        },
        "error_message": {
            "zh": "写入条目失败：{error}",
            "en": "Failed to write entry: {error}",
        },
    },
    "status": {
        "empty_message": {
            "zh": "🌱 {customer_id} 的 Journal 已激活（第 {started_day} 天），但还没有正式记录。下一步：/opc-journal record \"今天完成的第一件事\"",
            "en": "🌱 {customer_id}'s Journal is active (Day {started_day}), but no entries yet. Next step: /opc-journal record \"One thing you did today\"",
        },
        "active_message": {
            "zh": "📔 {customer_id} 从第 {started_day} 天开始，已经记录了 {entry_count} 条。最新：{latest}。",
            "en": "📔 {customer_id} started on Day {started_day} and has recorded {entry_count} entries. Latest: {latest}.",
        },
        "no_entries": {
            "zh": "还没有正式记录",
            "en": "No entries yet",
        },
    },
    "insights": {
        "journey_start": {
            "zh": "旅程开始",
            "en": "Journey Begins",
        },
        "journey_start_summary": {
            "zh": "所有的宏大故事都始于一个短句。你今天的记录，会成为未来回望时的第一块路标。",
            "en": "Every great story begins with a single sentence. Today's note will be the first marker you look back on.",
        },
        "rec_1_action": {
            "zh": "记录一件今天完成的、再小也算数的事",
            "en": "Record one small thing you achieved today — it counts",
        },
        "rec_1_rationale": {
            "zh": "第一天的仪式不是宏大叙事，而是证明自己来了",
            "en": "Day 1 ritual is not about grand narratives, but showing up",
        },
        "rec_2_action": {
            "zh": "写下一个你最想在 30 天后看到的变化",
            "en": "Write down one change you'd love to see in 30 days",
        },
        "rec_2_rationale": {
            "zh": "让未来的自己有东西可对比",
            "en": "Give your future self something to compare against",
        },
        "message_empty": {
            "zh": "第 {day} 天洞察——每一段旅程都从一张白纸开始。",
            "en": "Day {day} insight — every journey starts with a blank page.",
        },
        "message_normal": {
            "zh": "已为第 {day} 天生成洞察，基于最近 {days} 天的记录。",
            "en": "Insight generated for Day {day} from the last {days} day(s).",
        },
        "theme_overload": {
            "zh": "注意节奏",
            "en": "Watch Your Pace",
        },
        "summary_overload": {
            "zh": "本周记录了高强度工作信号，建议关注可持续性。",
            "en": "High-intensity work signals detected this week. Consider sustainability.",
        },
        "theme_pivot": {
            "zh": "战略反思期",
            "en": "Strategic Reflection",
        },
        "summary_pivot": {
            "zh": "连续的验证反馈提示可能需要重新审视当前方向。",
            "en": "Repeated validation feedback suggests revisiting your current direction.",
        },
        "theme_momentum": {
            "zh": "势能上升",
            "en": "Momentum Building",
        },
        "summary_momentum": {
            "zh": "本周有明确的推进信号，势能正在积累。",
            "en": "Clear forward signals this week — momentum is building.",
        },
        "theme_isolation": {
            "zh": "连接需求",
            "en": "Need Connection",
        },
        "summary_isolation": {
            "zh": "信号显示你可能在独自承担太多，需要外部连接。",
            "en": "Signals suggest you're carrying too much alone. Reach out.",
        },
        "theme_learning": {
            "zh": "快速成长",
            "en": "Rapid Growth",
        },
        "summary_learning": {
            "zh": "本周显示出强烈的学习曲线，新技能正在内化。",
            "en": "Strong learning curve this week — new skills are internalizing.",
        },
        "theme_default": {
            "zh": "持续积累",
            "en": "Steady Accumulation",
        },
        "summary_default": {
            "zh": "今天/本周的记忆显示平稳推进，没有特别强烈的信号。",
            "en": "This period shows steady progress without strong signals.",
        },
    },
    "analyze": {
        "no_sources": {
            "zh": "尚未找到 dreams.md 或 memory 文件。",
            "en": "No dreams.md or memory files found yet.",
        },
        "no_message": {
            "zh": "没有可用的记忆源",
            "en": "No memory sources available",
        },
        "success_message": {
            "zh": "已为 {customer_id} 完成模式分析",
            "en": "Pattern analysis complete for {customer_id}",
        },
        "style_conservative": {
            "zh": "谨慎型",
            "en": "Conservative",
        },
        "style_aggressive": {
            "zh": "进取型",
            "en": "Aggressive",
        },
        "style_balanced": {
            "zh": "平衡型",
            "en": "Balanced",
        },
        "help_independent": {
            "zh": "高度独立，较少主动求助",
            "en": "Highly independent, rarely seeks help",
        },
        "help_moderate": {
            "zh": "适度协作，遇到瓶颈时求助",
            "en": "Moderately collaborative, asks for help at blockers",
        },
        "help_frequent": {
            "zh": "频繁协作，善于利用外部支持",
            "en": "Frequently collaborative, leverages external support",
        },
        "rhythm_high": {
            "zh": "活跃",
            "en": "Active",
        },
        "rhythm_medium": {
            "zh": "中等",
            "en": "Moderate",
        },
        "rhythm_low": {
            "zh": "较低",
            "en": "Low",
        },
        "emotion_volatile": {
            "zh": "情绪起伏较大",
            "en": "High emotional volatility",
        },
        "emotion_stable": {
            "zh": "情绪相对稳定",
            "en": "Emotionally stable",
        },
        "emotion_mixed": {
            "zh": "情绪有波动但可控",
            "en": "Emotional fluctuations, but manageable",
        },
        "velocity_high": {
            "zh": "高",
            "en": "High",
        },
        "velocity_medium": {
            "zh": "中",
            "en": "Medium",
        },
        "velocity_low": {
            "zh": "低",
            "en": "Low",
        },
    },
    "milestones": {
        "first_product_launch": {
            "zh": "首次产品发布",
            "en": "First product launch",
        },
        "first_customer": {
            "zh": "获取第一位客户",
            "en": "Acquired first customer",
        },
        "revenue_milestone": {
            "zh": "收入里程碑",
            "en": "Revenue milestone",
        },
        "mvp_complete": {
            "zh": "MVP 完成",
            "en": "MVP completed",
        },
        "first_journal_entry": {
            "zh": "写下第一条日记",
            "en": "Recorded first journal entry",
        },
        "message": {
            "zh": "为 {customer_id} 检测到 {count} 个里程碑",
            "en": "Detected {count} milestones for {customer_id}",
        },
    },
    "task": {
        "missing_description": {
            "zh": "请提供任务描述（description 不能为空）",
            "en": "description is required",
        },
        "success_message": {
            "zh": "任务 {task_id} 已创建，预计完成时间：{eta}",
            "en": "Task {task_id} created, ETA: {eta}",
        },
    },
    "export": {
        "success_message": {
            "zh": "已为 {customer_id} 准备导出（格式：{fmt}）",
            "en": "Export prepared for {customer_id} ({fmt})",
        },
    },
    "search": {
        "success_message": {
            "zh": "已为 {customer_id} 准备搜索：{query}",
            "en": "Search prepared for {customer_id}: {query}",
        },
    },
    "emotions": {
        "平静": {"zh": "平静", "en": "calm"},
        "开心": {"zh": "开心", "en": "happy"},
        "焦虑": {"zh": "焦虑", "en": "anxious"},
        "沮丧": {"zh": "沮丧", "en": "frustrated"},
        "兴奋": {"zh": "兴奋", "en": "excited"},
        "疲惫": {"zh": "疲惫", "en": "tired"},
        "困惑": {"zh": "困惑", "en": "confused"},
        "放松": {"zh": "放松", "en": "relaxed"},
        "neutral": {"zh": "平静", "en": "neutral"},
    },
}


def _resolve_lang(args: dict) -> str:
    lang = args.get("lang", "") or args.get("language", "")
    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("en"):
        return "en"
    return DEFAULT_LANG


def t(key_path: str, args: dict = None, **kwargs) -> str:
    args = args or {}
    lang = _resolve_lang(args)
    parts = key_path.split(".")
    node = TEXTS
    for p in parts:
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return key_path
    if isinstance(node, dict):
        text = node.get(lang) or node.get(DEFAULT_LANG, list(node.values())[0] if node else key_path)
    else:
        text = node
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
