# opc-journal-suite

## Description

OPC200 User Journal Experience Suite - Complete growth tracking, memory management, and insight generation for One Person Companies (OPC). Includes journaling, pattern recognition, milestone tracking, async task management, and more.

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

OPC Journal Suite is a collection of OpenClaw Skills designed for One Person Company (OPC), providing:

- 📔 **Smart Journaling** - Automatic recording, linking, and retrieval of user journey
- 🧠 **Behavioral Pattern Recognition** - Identify work habits, decision patterns, growth trajectory
- 🎯 **Milestone Tracking** - Auto-detect important moments, generate achievement reports
- ⏰ **Async Task Management** - 7×24 background task execution and status sync
- 💡 **Insight Generation** - Personalized recommendations based on historical data

## Skills in this Suite

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `opc-journal-core` | Core journaling functions | "journal", "log", "summarize" |
| `opc-pattern-recognition` | Pattern analysis | "analyze my habits", "why do I always..." |
| `opc-milestone-tracker` | Milestone tracking | Auto-trigger + "I completed..." |
| `opc-async-task-manager` | Async tasks | "run in background", "get results tomorrow" |
| `opc-insight-generator` | Insight generation | "give me advice", "what should I do" |

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
│  ├── journal/entries/        # Journal entries              │
│  ├── journal/insights/       # Extracted insights           │
│  ├── journal/milestones/     # Milestones                   │
│  └── tasks/async/            # Async tasks                  │
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

User: "Just finished the product prototype, but a bit worried about tech stack choices"

System automatically:
- Creates journal entry JE-20260321-001
- Links to previous tech discussion JE-20260318-003
- Flags emotional state: "anxious_but_accomplished"
- Creates follow-up task for tech validation

### 3. Pattern Recognition (Weekly)

Auto-triggered every Sunday:
```
📊 Weekly Pattern Analysis

Work Rhythm:
• Peak hours: Wed afternoon, Fri morning
• Low hours: Mon morning
• Average focus duration: 2.3 hours

Decision Patterns:
• Risk appetite: Conservative
• Common hesitation points: Tech stack, pricing strategy
• Help-seeking timing: Usually 2 days after problem occurs

Recommendations:
"Try scheduling important decisions for Wed afternoon"
"Consider seeking tech advice 1 day earlier"
```

### 4. Milestone Detection

Auto-detected:
```
🎉 Milestone Achieved: First Product Launch

Day: 45
Time: 2026-03-21 14:30
Context: Independently completed full cycle from idea to launch

Previous milestone: MVP Completed (Day 28)
Next predicted: First Sale (Est. Day 52)
```

### 5. Async Task Example

User: "I need a competitive analysis report, due tomorrow morning"

Bot: "Got it! Created async task #RESEARCH-007
     Assigned to Research Agent
     Estimated completion: Tomorrow 8:00 AM
     Will send Feishu notification and generate summary when done"

[Next morning]
Bot: "☀️ #RESEARCH-007 Complete!
     Discovered 3 key insights, synced to your Journal"

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
# OPC200 Project Integration Configuration

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
