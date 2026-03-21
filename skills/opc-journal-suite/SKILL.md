# opc-journal-suite

## Description

OPC200 用户日志体验套件 - 为一人公司（OPC）提供完整的成长追踪、记忆管理和洞察生成能力。包含 Journal 记录、模式识别、里程碑追踪、异步任务管理等模块。

## Install

```bash
clawhub install coidea/opc-journal-core
clawhub install coidea/opc-pattern-recognition
clawhub install coidea/opc-milestone-tracker
clawhub install coidea/opc-async-task-manager
```

Or install the full suite:

```bash
clawhub install coidea/opc-journal-suite
```

## Overview

OPC Journal Suite 是一套专门为 One Person Company (OPC) 设计的 OpenClaw Skills，提供：

- 📔 **智能日志记录** - 自动记录、关联、检索用户旅程
- 🧠 **行为模式识别** - 识别工作习惯、决策模式、成长轨迹  
- 🎯 **里程碑追踪** - 自动检测重要时刻，生成成就报告
- ⏰ **异步任务管理** - 7×24 后台任务执行与状态同步
- 💡 **洞察生成** - 基于历史数据提供个性化建议

## Skills in this Suite

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `opc-journal-core` | 核心日志功能 | "记录", "journal", "总结一下" |
| `opc-pattern-recognition` | 模式识别 | "分析我的习惯", "为什么我总是..." |
| `opc-milestone-tracker` | 里程碑追踪 | 自动触发 + "我完成了..." |
| `opc-async-task-manager` | 异步任务 | "后台执行", "明早给我结果" |
| `opc-insight-generator` | 洞察生成 | "给我建议", "我该怎么办" |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPC Journal Suite                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Journal    │  │   Pattern    │  │  Milestone   │      │
│  │    Core      │◄─┤ Recognition  │◄─┤   Tracker    │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                   │
│         │  ┌──────────────┐  ┌──────────────┐              │
│         └──┤    Async     │  │   Insight    │              │
│            │  Task Mgr    │  │  Generator   │              │
│            └──────────────┘  └──────────────┘              │
│                                                             │
│  Shared Storage:                                            │
│  ├── journal/entries/        # 日志条目                     │
│  ├── journal/insights/       # 提炼洞察                     │
│  ├── journal/milestones/     # 里程碑                       │
│  └── tasks/async/            # 异步任务                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Initialize Journal for Customer

```bash
# Auto-triggered when new customer onboard
opc-journal-init --customer-id OPC-001 --day 1
```

### 2. Record Journal Entry

User: "今天完成了产品原型，但是有点担心技术选型"

System automatically:
- Creates journal entry JE-20260321-001
- Links to previous tech discussion JE-20260318-003
- Flags emotional state: "anxious_but_accomplished"
- Creates follow-up task for tech validation

### 3. Pattern Recognition (Weekly)

Auto-triggered every Sunday:
```
📊 本周模式分析

工作节奏:
• 高效时段: 周三下午、周五上午
• 低谷时段: 周一早晨
• 平均专注时长: 2.3 小时

决策模式:
• 风险偏好: 保守型
• 常见犹豫点: 技术选型、定价策略
• 求助时机: 通常在问题出现 2 天后

建议:
"尝试将重要决策安排在周三下午"
"考虑提前 1 天寻求技术建议"
```

### 4. Milestone Detection

Auto-detected:
```
🎉 里程碑达成: 首次产品发布

Day: 45
Time: 2026-03-21 14:30
Context: 独立完成从想法到上线的完整流程

Previous milestone: 完成 MVP (Day 28)
Next predicted: 首笔销售 (预计 Day 52)
```

### 5. Async Task Example

User: "我需要一份竞品分析报告，明天早上要"

Bot: "收到！已创建异步任务 #RESEARCH-007
     分配给 Research Agent
     预计完成: 明早 8:00
     完成后将发送飞书通知并生成摘要"

[Next morning]
Bot: "☀️ #RESEARCH-007 完成！
     发现 3 个关键洞察，已同步到您的 Journal"

## Configuration

```yaml
# ~/.openclaw/skills/opc-journal-suite/config.yml

journal:
  storage_path: "customers/{customer_id}/journal/"
  retention_days: 365
  privacy_level: "standard"  # standard / sensitive / vault
  
pattern_recognition:
  analysis_frequency: "weekly"
  insight_depth: "detailed"  # brief / detailed / deep
  
milestone:
  auto_detect: true
  celebration_enabled: true
  
async_task:
  max_concurrent: 5
  default_timeout: "8h"
  notification_channels: ["feishu", "email"]
```

## Integration with OPC200

```yaml
# OPC200 项目集成配置

opc200:
  deployment_modes:
    cloud_hosted:
      journal_storage: "centralized"
      pattern_analysis: "server_side"
      async_execution: "shared_pool"
      
    on_premise:
      journal_storage: "local_only"
      pattern_analysis: "local_with_sync"
      async_execution: "local_queue"
      privacy: "maximum"
      
    edge_node:
      journal_storage: "hybrid"
      pattern_analysis: "distributed"
      async_execution: "edge_cloud_coordinated"

support_hub:
  access_levels:
    - view_anonymous_patterns    # 脱敏模式分析
    - read_journal_with_consent  # 授权后访问
    - emergency_override         # 紧急访问（审计）
```

## API Reference

### Journal Core

```python
# Create entry
journal.create_entry(
    customer_id="OPC-001",
    content="用户输入内容",
    context={
        "agents_involved": ["Support"],
        "tasks_created": ["TASK-001"],
        "emotional_state": "confident"
    }
)

# Retrieve with context
entries = journal.query(
    customer_id="OPC-001",
    topic="pricing_strategy",
    time_range="last_30_days",
    include_related=True
)

# Generate digest
digest = journal.generate_digest(
    customer_id="OPC-001",
    period="weekly",
    format="markdown"
)
```

### Pattern Recognition

```python
# Analyze patterns
patterns = pattern_analyzer.analyze(
    customer_id="OPC-001",
    dimensions=["work_hours", "decision_style", "stress_triggers"],
    time_range="last_90_days"
)

# Predict behavior
prediction = pattern_analyzer.predict(
    customer_id="OPC-001",
    scenario:"product_launch"
)
```

### Async Task Manager

```python
# Create async task
task = async_manager.create(
    customer_id="OPC-001",
    task_type:"research",
    description:"竞品分析报告",
    deadline:"tomorrow 08:00",
    agent:"ResearchAgent"
)

# Check status
status = async_manager.status(task.id)

# On completion
async_manager.on_complete(task.id, callback=notify_user)
```

## Directory Structure

```
opc-journal-suite/
├── README.md
├── SKILL.md                      # This file
├── config.yml                    # Default configuration
│
├── opc-journal-core/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── init.py
│   │   ├── record.py
│   │   ├── query.py
│   │   └── digest.py
│   └── templates/
│       └── entry_template.yml
│
├── opc-pattern-recognition/
│   ├── SKILL.md
│   └── scripts/
│       ├── analyzer.py
│       ├── patterns.py
│       └── predictor.py
│
├── opc-milestone-tracker/
│   ├── SKILL.md
│   └── scripts/
│       ├── detector.py
│       ├── reporter.py
│       └── celebration.py
│
├── opc-async-task-manager/
│   ├── SKILL.md
│   └── scripts/
│       ├── scheduler.py
│       ├── executor.py
│       └── notifier.py
│
└── opc-insight-generator/
    ├── SKILL.md
    └── scripts/
        ├── generator.py
        └── recommender.py
```

## Development Roadmap

| Version | Features | ETA |
|---------|----------|-----|
| v1.0 | Core journal, basic patterns | 2026.03 |
| v1.1 | Milestone auto-detection | 2026.04 |
| v1.2 | Advanced async tasks | 2026.04 |
| v2.0 | Cross-customer insights (anonymized) | 2026.05 |
| v2.5 | Voice journal, emotional AI | 2026.06 |

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests
4. Submit PR

## License

MIT License - OPC200 Project

## Support

- GitHub Issues: https://github.com/coidea-sys/opc-journal-suite/issues
- OPC200 Support: feishu://opc200-support
- Documentation: https://docs.opc200.co/journal-suite
