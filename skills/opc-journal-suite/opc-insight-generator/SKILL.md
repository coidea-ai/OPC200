# opc-insight-generator

## Description

OPC Journal Suite 洞察生成模块 - 基于 Journal 和模式识别，主动提供个性化建议、预警和机会发现。

## When to use

- 用户问"我该怎么办"、"给我建议"、"下一步做什么"
- 系统检测到机会或风险时主动推送
- 周期性生成策略建议
- 帮助用户突破瓶颈

## Insight Types

### 1. 机会洞察 (Opportunity)

```python
# 基于数据的主动建议
insight = {
    type: "opportunity",
    confidence: 0.85,
    
    observation: "您本周有 3 个晚上的工作时间，
                  且您曾表示想学习视频剪辑",
    
    recommendation: "可以利用这些时间启动您的 YouTube 频道计划",
    
    supporting_data: {
        available_time: "12 hours/week",
        expressed_interest: "2026-03-15",
        market_opportunity: "您的领域在 YouTube 增长 40%"
    },
    
    next_steps: [
        "确定前 5 个视频主题",
        "准备基础设备清单",
        "制定发布节奏（建议周更）"
    ],
    
    urgency: "medium"
}
```

### 2. 风险预警 (Risk Alert)

```python
insight = {
    type: "risk_alert",
    confidence: 0.78,
    severity: "medium",
    
    observation: "您已连续 5 天工作超过 10 小时，
                  且昨天提到'有点 burnout'",
    
    risk: "过度工作导致的创造力下降和健康风险",
    
    recommended_actions: [
        "明天安排半天休息",
        "将非紧急任务推迟到下周",
        "考虑委托更多任务给 Agent"
    ],
    
    auto_triggered: true
}
```

### 3. 效率建议 (Efficiency)

```python
insight = {
    type: "efficiency",
    confidence: 0.92,
    
    observation: "您每次写邮件平均花费 45 分钟，
                  且内容结构高度相似",
    
    recommendation: "创建邮件模板库，预计节省 60% 时间",
    
    quick_win: true,  # 快速收益
    
    implementation: "我可以帮您:
        1. 分析过去 20 封邮件提取模式
        2. 生成 5 个常用模板  
        3. 设置快捷插入命令"
}
```

### 4. 成长建议 (Growth)

```python
insight = {
    type: "growth",
    based_on: "growth_trajectory_analysis",
    
    current_stage: "技术能力快速提升期",
    next_stage: "业务规模化期",
    
    gap_analysis: {
        strong: ["产品开发", "AI 协作", "快速迭代"],
        weak: ["销售转化", "定价策略", "客户留存"]
    },
    
    recommended_focus: "未来 30 天专注提升销售能力",
    
    resources: [
        "推荐 Skill: opc-sales-playbook",
        "推荐任务: 分析 10 个成功转化案例",
        "建议连接: 与 OPC-089 交流（相似背景，销售能力强）"
    ]
}
```

## Generation Triggers

### 主动触发 (Proactive)

```python
# 定期生成
scheduled_insights = {
    "weekly_review": {
        "when": "sunday_evening",
        "content": "下周机会与风险提示"
    },
    "monthly_strategy": {
        "when": "last_day_of_month", 
        "content": "月度成长建议与下月重点"
    }
}

# 事件触发
event_triggers = {
    "milestone_reached": "生成下一阶段建议",
    "stuck_for_3_days": "生成突破建议",
    "high_energy_detected": "建议推进重要任务",
    "low_energy_streak": "建议休息或调整"
}
```

### 被动触发 (On-Demand)

User: "我卡住了，不知道该怎么办"

System:
```python
# 分析当前状态
current_situation = analyze_journal(
    time_range="last_7_days",
    focus="blockers_and_patterns"
)

# 生成针对性建议
insight = generate_insight(
    situation=current_situation,
    type="breakthrough",
    personalization_level="high"
)
```

Response:
```
🤔 我理解您的感受

我分析了您过去 7 天的 Journal，发现:

🔍 当前状态
• 您正在处理技术架构重构（Day 3）
• 提到了 3 次"不知道选哪个方案"
• 但您也独立解决了 2 个类似复杂问题

💡 我的观察
这和 Day 23 的情况很像——当时您也在技术选型上纠结了 3 天，
最后通过"快速原型对比"方法做出了决策，而且结果很好。

🎯 建议尝试
1. 为每个方案创建最小原型（各用 2 小时）
2. 列出 3 个必须满足的标准
3. 明天下午（您的高效时段）做决策

📚 相关资源
• 您 Day 23 的决策记录: [链接]
• 技术选型框架 Skill: [安装]

需要我帮您创建原型任务吗？
```

## Insight Quality Framework

```python
# 洞察质量评估
quality_score = calculate_quality(
    relevance=0.9,      # 与用户当前情况的相关度
    actionability=0.8,  # 可执行性
    novelty=0.6,        # 不是显而易见的东西
    personalization=0.9, # 基于用户特定数据
    timeliness=0.85     # 时机合适
)

# 只推送高质量洞察
if quality_score > 0.75:
    deliver_insight(insight)
else:
    # 存入待精炼池
    refinement_queue.add(insight)
```

## Insight Presentation

### 格式: 卡片式

```
┌─────────────────────────────────────────────────────────┐
│  💡 洞察 #INS-20260321-001                               │
│  类型: 效率提升 | 置信度: 92%                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 观察                                                 │
│  您处理客户咨询的平均响应时间: 4 小时                    │
│  且 60% 的问题是重复的                                   │
│                                                          │
│  💡 建议                                                 │
│  创建 FAQ 自动回复系统                                   │
│  预计节省: 每周 6 小时                                   │
│                                                          │
│  🚀 快速开始                                             │
│  [分析我的常见问题] → [生成回复模板] → [设置自动回复]    │
│                                                          │
│  ⏰ 时机                                                 │
│  建议本周实施，下周开始享受收益                          │
│                                                          │
│  [✅ 接受建议] [🤔 了解更多] [❌ 忽略]                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 格式: 对话式

```
Bot: 我注意到一个模式...

您每次开始新项目时，都会花很多时间在选择技术栈上。
上次用了 3 天，这次已经 2 天了。

但这似乎没有影响最终项目的成功——
您的 Day 12 项目和 Day 34 项目都很成功。

我有个想法：
也许您可以创建一个"技术选型决策框架"，
把您的评估标准固化下来，
这样以后类似决策可以更快。

需要我帮您整理您过去的决策逻辑吗？
```

## Configuration

```yaml
insight_generator:
  generation:
    proactive:
      enabled: true
      max_per_day: 3  # 避免信息过载
      min_quality_score: 0.75
      
    scheduled:
      weekly: "sunday_19:00"
      monthly: "last_day_20:00"
      
  delivery:
    channels: ["feishu", "journal"]
    format: "adaptive"  # card / conversational / detailed
    
  personalization:
    use_patterns: true
    use_goals: true
    use_preferences: true
    similar_customers_anonymous: true
    
  feedback_loop:
    track_accepted: true
    track_ignored: true
    track_implemented: true
    improve_based_on_feedback: true
```

## Best Practices

1. **数据驱动** - 每个建议都有数据支撑
2. **时机敏感** - 在合适的时间推送（不在深夜打扰）
3. **行动导向** - 不只是"你知道吗"，而是"你可以这样做"
4. **尊重边界** - 用户可以说"不"，系统不重复推送
5. **持续学习** - 跟踪建议的接受率和效果，不断改进
