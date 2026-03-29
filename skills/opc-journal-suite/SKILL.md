# opc-journal-suite

**Version**: 2.3.0  
**Status**: Production Ready  
**Last Updated**: 2026-03-30

## Description

OPC200 User Journal Experience Suite - Complete growth tracking, memory management, and insight generation for One Person Companies (OPC). Includes journaling, pattern recognition, milestone tracking, async task management, and more.

**LOCAL-ONLY**: This is a local-only skill. No network calls, no external APIs, no data sharing. All data is stored in customer-scoped local directories only.

This is a **coordinating skill** that routes user intents to appropriate sub-skills.

## Install

Install the full suite (coordinating skill + all sub-skills):

```bash
clawhub install coidea/opc-journal-suite
```

Or install individual sub-skills:

```bash
clawhub install coidea/opc-journal-core
clawhub install coidea/opc-pattern-recognition
clawhub install coidea/opc-milestone-tracker
clawhub install coidea/opc-async-task-manager
clawhub install coidea/opc-insight-generator
```

## Overview

OPC Journal Suite is a collection of OpenClaw Skills designed for One Person Company (OPC), providing:

- 📔 **Smart Journaling** - Automatic recording, linking, and retrieval of user journey
- 🧠 **Behavioral Pattern Recognition** - Identify work habits, decision patterns, growth trajectory
- 🎯 **Milestone Tracking** - Auto-detect important moments, generate achievement reports
- ⏰ **Async Task Management** - Local task creation and tracking (no external execution)
- 💡 **Insight Generation** - Personalized recommendations based on historical data

**Privacy First**: All processing is local. No data leaves your machine.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPC Journal Suite                         │
│              (Coordinating Skill - Unified Entry)            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Intent Detection & Routing                │   │
│  │         (scripts/coordinate.py - 25 tests)          │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│         ┌────────────────┼────────────────┐               │
│         │                │                │               │
│         ▼                ▼                ▼               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │   Journal    │ │   Pattern    │ │  Milestone   │      │
│  │    Core      │ │ Recognition  │ │   Tracker    │      │
│  └──────┬───────┘ └──────────────┘ └──────────────┘      │
│         │                                                  │
│         │  ┌──────────────┐ ┌──────────────┐             │
│         └──┤    Async     │ │   Insight    │             │
│            │  Task Mgr    │ │  Generator   │             │
│            └──────────────┘ └──────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Unified Entry Point

Instead of calling individual sub-skills, use the suite as a unified entry point:

### Intent-Based Routing

The suite automatically detects user intent and routes to the appropriate sub-skill:

| User Says | Detected Intent | Routed To |
|-----------|-----------------|-----------|
| "Record my progress today" | `journal_record` | opc-journal-core |
| "分析我的工作习惯" | `pattern_analyze` | opc-pattern-recognition |
| "Detect milestones in my journey" | `milestone_detect` | opc-milestone-tracker |
| "Run this in background" | `task_create` | opc-async-task-manager |
| "Give me advice on what to do" | `insight_generate` | opc-insight-generator |

### Usage

```python
# Unified entry - suite routes to correct sub-skill
result = opc_journal_suite.coordinate(
    customer_id="OPC-001",
    input={"text": "Record my progress today"}
)

# Result includes delegation info
{
    "status": "success",
    "result": {
        "action": "delegate",
        "delegation": {
            "intent": "journal_record",
            "confidence": 0.85,
            "target_skill": "opc-journal-core",
            "customer_id": "OPC-001"
        }
    }
}
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
     Estimated completion: Tomorrow 8:00 AM
     Will generate summary when done"

[Next morning]
Bot: "☀️ #RESEARCH-007 Ready!
     Discovered 3 key insights, synced to your Journal"

**Note**: Tasks are tracked locally. No external execution or notification services are used.

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
  # NOTE: Notification channels are reserved for future versions
  # Current implementation is local-only
```

## Data Privacy & Security

### Local-Only Design
- ✅ All data stored in `~/.openclaw/customers/{customer_id}/`
- ✅ No network calls
- ✅ No external APIs
- ✅ No data sharing
- ✅ No credentials required

### Privacy Levels
```yaml
privacy_level: "standard"   # Normal operation
privacy_level: "sensitive"  # Extra care with personal data
privacy_level: "vault"      # Maximum privacy, minimal retention
```

### Data Retention
- Configurable `retention_days` (default: 365)
- Automatic cleanup of old entries
- Customer-scoped isolation

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
# Create async task (local tracking only)
task = async_manager.create(
    customer_id="OPC-001",
    task_type:"research",
    description:"竞品分析报告",
    deadline:"tomorrow 08:00"
)

# Check status
status = async_manager.status(task.id)

# Task results are stored locally, no external callbacks
```

## Directory Structure

```
opc-journal-suite/
├── README.md
├── SKILL.md                      # This file
├── config.yml                    # Default configuration
├── scripts/
│   └── coordinate.py             # Intent routing (25 tests)
├── tests/
│   ├── __init__.py
│   └── test_coordinate.py        # Coordination tests (25 cases)
│
├── opc-journal-core/             # Sub-skill (11 tests)
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── init.py
│   │   ├── record.py
│   │   ├── search.py
│   │   └── export.py
│   └── tests/
│       └── test_core.py
│
├── opc-pattern-recognition/      # Sub-skill (4 tests)
│   ├── SKILL.md
│   ├── scripts/
│   │   └── analyze.py
│   └── tests/
│       └── test_patterns.py
│
├── opc-milestone-tracker/        # Sub-skill (6 tests)
│   ├── SKILL.md
│   ├── scripts/
│   │   └── detect.py
│   └── tests/
│       └── test_milestones.py
│
├── opc-async-task-manager/       # Sub-skill (6 tests)
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── create.py
│   │   └── status.py
│   └── tests/
│       └── test_tasks.py
│
└── opc-insight-generator/        # Sub-skill (3 tests)
    ├── SKILL.md
    ├── scripts/
    │   └── daily_summary.py
    └── tests/
        └── test_insights.py
```

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| opc-journal-suite (coordination) | 25 | ✅ Pass |
| opc-journal-core | 11 | ✅ Pass |
| opc-pattern-recognition | 4 | ✅ Pass |
| opc-milestone-tracker | 6 | ✅ Pass |
| opc-async-task-manager | 6 | ✅ Pass |
| opc-insight-generator | 3 | ✅ Pass |
| **Total** | **55** | ✅ **All Pass** |

All tests are local unit tests with no network dependencies.

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
- Documentation: https://docs.opc200.co/journal-suite

**Note**: This is a local-only skill. For support, please open a GitHub issue rather than using external channels.
