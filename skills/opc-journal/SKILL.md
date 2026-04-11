---
name: opc-journal
description: "OPC200 Journal - A CLI-style single skill for One Person Company growth tracking. Record entries, analyze patterns from dreams/memory, detect milestones, and generate insights. LOCAL-ONLY: no network calls."
user-invocable: true
command-dispatch: tool
tool: main
command-arg-mode: raw
metadata:
  {
    "openclaw": {
      "emoji": "📔",
      "always": false,
      "requires": {}
    }
  }
---

# opc-journal

**Version**: 2.4.2  
**Type**: Single CLI-style Skill  
**Status**: Active

> 这是 `opc-journal-suite` 的 CLI 化重组版本。不再拆分为 5 个子 skill，而是统一为一个 `opc-journal` 入口，通过子命令调用功能。

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
| `task` | Create async task (legacy) | `/opc-journal task --description "Research"` |
| `status` | Show journal status | `/opc-journal status` |
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
│       ├── analyze.py    # v2.4 interpretation layer
│       ├── milestones.py
│       ├── insights.py
│       ├── task.py
│       └── status.py
├── utils/
│   └── storage.py
├── tests/
└── config.yml
```

## Development Note

- `analyze` 从 dreams.md / memory/*.md 读取，做 OPC 特定解读
- `insights` 从记忆文件生成业务洞察和建议
- 所有数据存储在 `~/.openclaw/customers/{customer_id}/`
- 完全本地运行，无外部网络调用
