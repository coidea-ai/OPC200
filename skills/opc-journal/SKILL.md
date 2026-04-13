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

**Version**: 2.5.1  
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
| `batch-task` | Create multiple async tasks | `/opc-journal batch-task --descriptions "A" "B" "C"` |
| `status` | Show journal status | `/opc-journal status` |
| `delete` | Delete an entry by entry_id | `/opc-journal delete --entry-id JE-20260413-AB12CD` |
| `archive` | Archive all journal data | `/opc-journal archive --clear` |
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
│       ├── batch_task.py
│       ├── status.py
│       ├── delete.py
│       ├── archive.py
│       └── update_meta.py
├── utils/
│   └── storage.py
├── tests/
└── config.yml
```

## Development Notes

- `analyze` reads `dreams.md` and `memory/*.md` and returns **structural signals + keyword fragments** for the caller (LLM) to interpret dynamically. Structural signals are purely quantitative (punctuation counts, caps, etc.). Keyword fragments use minimal regex patterns for common action/challenge/achievement words, but no emotional interpretation is baked in.
- `insights` returns **raw memory context and signal counts** for the caller (LLM) to generate recommendations dynamically. Includes keyword-based signal counts but defers semantic interpretation to the caller.
- `milestones` returns a **raw candidate object** for the caller (LLM) to validate and classify. No keyword-based auto-detection.
- `record` defers emotional interpretation to the caller. The `emotion` frontmatter field is only populated if the caller provides it in `metadata`.
- `task` creates a single async task record; `batch-task` creates multiple tasks in one call.
- `delete` removes an entry by `entry_id`, creates a `.bak` before modification, and updates the total count in meta. **Requires `--force` flag for destructive operations.**
- `archive` copies all memory files and `journal_meta.json` to a timestamped `archive/` directory. Use `--clear` to reset the journal after archiving. **Requires `--force` flag when using `--clear`.**
- `update-meta` updates journal metadata (language, goals, preferences). Retroactive translation rules are kept minimal because templates are now English-only by design.
- All data is stored locally under `~/.openclaw/customers/{customer_id}/`.
- No external network calls are made.
