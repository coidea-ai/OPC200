---
name: opc-journal
description: "OPC200 Journal - A CLI-style single skill for One Person Company growth tracking. Record entries, analyze patterns from dreams/memory, detect milestones, and generate insights. LOCAL-ONLY: no network calls."
user-invocable: true
command-dispatch: tool
tool: main
command-arg-mode: raw
metadata:
  openclaw:
    emoji: "📔"
    always: false
    requires: {}
---

# opc-journal

**Version**: 2.4.3  
**Type**: Single CLI-style Skill  
**Status**: Active

> A unified CLI entrypoint for journaling, pattern analysis, milestone detection, insights, and task tracking.

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize journal for customer | `/opc-journal init --day 1` |
| `record` | Record a journal entry | `/opc-journal record "Shipped MVP"` |
| `search` | Search entries | `/opc-journal search --query pricing` |
| `export` | Export journal | `/opc-journal export --format markdown` |
| `analyze` | Analyze patterns from memory | `/opc-journal analyze --days 7` |
| `milestones` | Detect milestones | `/opc-journal milestones --content "First sale!"` |
| `insights` | Generate daily/weekly insights | `/opc-journal insights --day 7` |
| `task` | Create async task | `/opc-journal task --description "Research"` |
| `status` | Show journal status | `/opc-journal status` |
| `update-meta` | Update metadata and language | `/opc-journal update-meta --language en` |
| `help` | Show help | `/opc-journal help` |

## Architecture

```
opc-journal/
├── scripts/
│   ├── main.py           # CLI entry point
│   └── commands/
│       ├── init.py
│       ├── record.py
│       ├── search.py
│       ├── export.py
│       ├── analyze.py
│       ├── milestones.py
│       ├── insights.py
│       ├── task.py
│       ├── status.py
│       └── update_meta.py
├── utils/
│   └── storage.py
├── tests/
└── config.yml
```

## Development Notes

- `analyze` reads `dreams.md` and `memory/*.md` to produce OPC-specific interpretations.
- `insights` generates business insights and recommendations from memory files.
- `update-meta` supports retroactive document translation when switching languages.
- All data is stored locally under `~/.openclaw/customers/{customer_id}/`.
- No external network calls are made.
