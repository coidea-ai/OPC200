# OPC Journal - User Guide

> Your personal, local-first journaling system.

## What is OPC Journal?

**OPC Journal** is a privacy-first journaling skill designed for one-person companies and individual knowledge workers. Everything stays on your local machine — no data leaves, no cloud dependencies, no external APIs.

Unlike traditional journaling apps, OPC Journal follows an **interpretation-first architecture**. It doesn't pretend to understand your emotions or draw rigid conclusions. Instead, it extracts **raw signals and structured context** from your entries and hands the interpretation to your assistant — which actually understands nuance, language, and context.

---

## Core Philosophy

- **Local-Only**: All data is stored in `~/.openclaw/customers/{id}/`
- **Interpretation-First**: No hardcoded psychology. No keyword guessing. Pure data, rich interpretation.
- **Frictionless**: Append-only by default. Search, export, archive when you need to.
- **Safe by Design**: Backups before every mutation. File locking for concurrent access.

---

## Quick Start

### 1. Initialize Your Journal

```bash
opc-journal init --customer-id Danny --day 1 --goals "Launch MVP" "Get first 100 users"
```

This creates your customer directory and writes a **charter** — your founding document.

### 2. Record Your First Entry

```bash
opc-journal record --customer-id Danny "Today I sketched the landing page and felt oddly confident."
```

Entries are appended to today's memory file automatically.

### 3. Check Status

```bash
opc-journal status --customer-id Danny
```

Shows total entries, date range, streaks, and language preference.

### 4. Search the Past

```bash
opc-journal search --customer-id Danny --query "confident"
```

Searches across all entries and returns matching blocks with context.

---

## Feature List

### 13 Commands at a Glance

| # | Command | What It Does |
|---|---------|--------------|
| 1 | `init` | Create journal charter and set goals |
| 2 | `record` | Append a journal entry with auto-generated ID |
| 3 | `search` | Full-text search across all entries locally |
| 4 | `export` | Export entries to Markdown or JSON |
| 5 | `analyze` | Extract structural signals (punctuation, caps, quotes) |
| 6 | `insights` | Build context summary for interpretation |
| 7 | `milestones` | Detect milestone candidates from recent entries |
| 8 | `status` | View journal statistics and streaks |
| 9 | `task` | Create a persistent async task |
| 10 | `batch-task` | Create multiple tasks at once |
| 11 | `delete` | Remove a specific entry by ID |
| 12 | `archive` | Copy entries to a timestamped archive |
| 13 | `update-meta` | Update language, goals, and preferences |

---

## Common Workflows

### Daily Standup Workflow
```bash
# Morning: Check your status
opc-journal status --customer-id Danny

# Log your work
opc-journal record --customer-id Danny "Refactored auth module. Blocked on API rate limits."

# End of day: Create tomorrow's tasks
opc-journal batch-task --customer-id Danny --descriptions "Email API support" "Draft rate limit workaround"
```

### Weekly Review Workflow
```bash
# Analyze the past week
opc-journal analyze --customer-id Danny --days 7

# Generate insights
opc-journal insights --customer-id Danny --days 7

# Export to share with advisor/coach
opc-journal export --customer-id Danny --time-range 7d --output-path ~/weekly.md

# Archive old entries to keep things tidy
opc-journal archive --customer-id Danny --clear
```

### Milestone Tracking Workflow
```bash
# Record a potential milestone
opc-journal record --customer-id Danny "Just got our first paying customer!" --emotion excited

# Detect milestones from recent entries
opc-journal milestones --customer-id Danny --days 7

# Update your goals based on progress
opc-journal update-meta --customer-id Danny --goals "Reach 10 customers" "Hire first contractor"
```

---

## Command Reference

### `init` — Initialize Your Journal

```bash
opc-journal init --customer-id Danny --day 1 \
  --goals "Launch product" "Reach ramen profitability" \
  --preferences '{"timezone": "Asia/Shanghai", "auto_record_daily": true, "review_schedule": ["weekly", "monthly", "quarterly"]}' \
  --language en
```

**What happens:**
- Creates `~/.openclaw/customers/Danny/`
- Writes `journal_meta.json` with your goals
- Creates today's memory file with a `type: charter` block
- Sets default preferences for auto-recording and review schedules

**Flags:**
- `--customer-id`: **Required**. Unique customer identifier
- `--day`: Starting day number (default: 1)
- `--goals`: List of string goals
- `--preferences`: JSON object for timezone, communication style, auto_record_daily, review_schedule
- `--language`: Force language (`zh` or `en`). Auto-detected if omitted.

---

### `record` — Write an Entry

```bash
opc-journal record "Shipped the auth flow. Sleep deprived but happy." \
  --day 12 --emotion excited
```

**What happens:**
- Appends entry to `memory/DD-MM-YY.md`
- Auto-generates an entry ID like `JE-20260413-A1B2C3`
- Backs up existing file to `.bak` before appending
- Updates `total_entries` in meta

**Flags:**
- `--day`: Day number (optional)
- `--emotion`: Caller-provided emotion tag (optional)
- `--content`: The entry body (required if not passed as positional arg)

**Tip:** If you don't provide `--emotion`, none is added. The caller can infer it from context later.

---

### `search` — Find Entries

```bash
# Basic search
opc-journal search --query "burnout"

# Case-sensitive, limited to 5 results
opc-journal search --query "MVP" --case-sensitive --limit 5
```

**Returns:**
- List of matching entries
- Match positions with surrounding context snippets
- Total match count and returned count

**Flags:**
- `--query`: Search string (default: "" returns all entries)
- `--limit`: Maximum results (default: 10)
- `--case-sensitive`: Enable exact case matching

---

### `export` — Export Your Journal

```bash
# Markdown export
opc-journal export --format markdown

# Last 7 days only
opc-journal export --time-range 7d --output-path ~/weekly.md

# JSON export
opc-journal export --format json --time-range 30d
```

**Supported formats:** `markdown`, `json`

**Flags:**
- `--format`: Output format (`markdown` or `json`, default: `markdown`)
- `--time-range`: Date filter (`7d`, `1w`, `1m`, `all`, default: `all`)
- `--output-path`: Custom file path for the exported file

**Output:**
- Markdown: Formatted document with headers and entry bodies
- JSON: Structured data with metadata, dates, and content

---

### `analyze` — Structural Signal Extraction

```bash
opc-journal analyze --days 14
```

**What it does:**
Extracts **language-agnostic structural signals** and **minimal keyword fragments** for interpretation:

**Structural signals** (purely quantitative):
- `exclamation_marks`: Count of `!`
- `question_marks`: Count of `?`
- `all_caps_words`: Number of ALL CAPS words
- `repeated_punctuation`: Patterns like `!!`, `??`, `...`
- `quoted_phrases`: Text inside quotation marks

**Keyword fragments** (light semantic extraction):
- `action_fragments`: Sentences containing action words (decided, choose, switch, adopt, finalize)
- `achievement_fragments`: Sentences containing completion words (completed, launched, shipped, sale, MVP, milestone)
- `obstacle_fragments`: Sentences containing obstacle words (stuck, blocked, bottleneck, failed, error, bug, issue)

**Why this design:**
- Structural signals work in any language (Chinese, English, Japanese)
- Keyword fragments provide quick context without rigid emotional interpretation
- The caller sees both the numbers and the actual text, and can interpret a high `exclamation_marks` count as excitement *or* frustration — depending on context.

**Note:** This is "minimal semantic processing" — not "zero semantic processing." The skill extracts keyword patterns but defers emotional/psychological interpretation to the caller.

---

### `insights` — Context for Interpretation

```bash
opc-journal insights --days 30
```

**What it does:**
Collects themes, signal summaries, and raw entry context into a single payload designed for interpretation.

**Returns:**
- `signal_summary`: Aggregated counts including:
  - Structural signals (punctuation, caps, repeated punctuation)
  - Keyword-based signal counts (action, challenge, learning, pivot — matched via minimal regex patterns)
- `themes`: Extracted keywords and repeated topics
- `recent_entries`: Full text of recent entries
- `generated_at`: ISO timestamp

**Use case:** Feed this into your preferred assistant or tool for personalized coaching or reflection.

**Note:** Like `analyze`, `insights` performs lightweight keyword counting but does **not** draw emotional conclusions. The caller interprets the patterns.

---

### `milestones` — Milestone Detection

```bash
opc-journal milestones --days 7
```

**What it does:**
Scans entries for milestone indicators (first entry, significant events, pattern breaks) and returns a **raw candidate object**.

**Returns:**
- `milestone_type`: e.g., `first_entry`, `pattern_break`
- `entry_id`: Linked entry
- `description`: Raw signal summary
- `confidence`: Structural score (0-1)

**Note:** The caller decides whether this is truly a milestone worth celebrating.

---

### `status` — Journal Health Check

```bash
opc-journal status
```

**Returns:**
- `total_entries`: Lifetime count
- `first_entry_date`: Oldest entry date
- `last_entry_date`: Most recent entry date
- `streak_days`: Consecutive days with entries
- `goals`: Your active goals
- `language`: Current language preference

---

### `task` — Create a Persistent Task

```bash
opc-journal task --type research \
  --description "Investigate competitor pricing strategies" \
  --timeout-hours 24
```

**What happens:**
- Creates a task ID like `TASK-20260413-A1B2C3`
- Persists to `tasks.json` with file locking
- Sets status to `created`

**Flags:**
- `--type`: Task category (default: `research`)
- `--description`: Task details (required)
- `--timeout-hours`: Expected turnaround (default: 8)

**Note:** Tasks survive process restarts. Use `batch-task` for bulk creation.

---

### `batch-task` — Create Multiple Tasks

```bash
opc-journal batch-task --descriptions \
  "Draft blog post" \
  "Email investor update" \
  "Review Q2 metrics" \
  --timeout-hours 24
```

**Flags:**
- `--descriptions`: List of task descriptions (required, space-separated)
- `--type`: Task category for all tasks (default: `research`)
- `--timeout-hours`: Expected turnaround time for all tasks (default: 8)

**Returns:**
- List of created task IDs
- Summary count
- Validation errors (if any descriptions are empty)

---

### `delete` — Remove an Entry

```bash
opc-journal delete --entry-id JE-20260413-A1B2C3 --force
```

**What happens:**
- Finds the entry across all memory files
- Creates a `.bak` backup
- Removes the entry block while preserving separators
- If the file becomes empty (and contains no charter), deletes the file
- Updates `total_entries` in meta

**Safety:**
- **Requires `--force`** to confirm the destructive operation
- Cannot delete without a valid `entry_id`
- `.bak` files are always created before mutation

---

### `archive` — Archive Old Entries

```bash
# Copy entries to archive folder
opc-journal archive

# Copy and clear source files (destructive)
opc-journal archive --clear --force
```

**What happens:**
- Copies all `*.md` files to `archive/YYYYMMDD-HHMMSS/`
- **Note:** `.bak` backup files are excluded from archiving
- With `--clear`: deletes source `.md` and `.bak` **only if** all copies succeeded

**Safety:**
- `archive --clear` will fail if any copy operation fails
- `archive --clear` **requires `--force`** for confirmation
- Backup files (`.bak`) remain in `memory/` even after `--clear` for safety

---

### `update-meta` — Update Preferences

```bash
opc-journal update-meta --language zh --goals "发布产品" "获取前100名用户"
```

**Flags:**
- `--language`: `zh` or `en`
- `--goals`: List of goal strings (replaces existing)
- `--day`: Update current day number

**Note:** Changing language does **not** retroactively translate entries.

### `help` — Show Command Help

```bash
opc-journal help
```

Displays the full list of available commands and their usage.

---

## File Structure

```
~/.openclaw/customers/Danny/
├── memory/
│   ├── 13-04-26.md          # Today's entries
│   ├── 13-04-26.md.bak      # Backup before last mutation
│   ├── 12-04-26.md          # Yesterday's entries
│   └── dreams.md            # Optional dream journal
├── archive/
│   └── 20260413-235959/     # Timestamped archive
│       └── 12-04-26.md
├── journal_meta.json        # Goals, language, stats, auto_record, review_schedule
└── tasks.json               # Persistent async tasks
```

---

## Best Practices

### 1. Write Daily
The value compounds. Even a single sentence is enough.

### 2. Use `analyze` + `insights` Together
Run `analyze` for raw signals, then `insights` for contextual data. Feed both to your preferred tool for the richest reflections.

### 3. Archive Monthly
Keep your `memory/` directory lean by archiving old entries:

```bash
opc-journal archive --customer-id Danny --clear
```

### 4. Back Up Your Customer Directory
Since everything is local, your journal is only as safe as your backups:

```bash
tar -czf opc-journal-backup.tar.gz ~/.openclaw/customers/Danny/
```

### 5. Task Timeout as Intention
The `--timeout-hours` on tasks isn't enforced by code — it's a **commitment device**. Use it to set expectations with yourself or your assistant.

---

## Troubleshooting

### "No memory directory found"
You haven't recorded any entries yet. Run `opc-journal init --customer-id <name>` followed by `opc-journal record --customer-id <name>`.

### "Entry not found"
Double-check the entry ID. Entry IDs are case-sensitive and look like `JE-20260413-A1B2C3`.

### Export is empty
Either you have no entries in the requested time range, or the date format in your files doesn't match the expected `dd-mm-yy` pattern.

### Tasks disappear after restart
You're on a version older than v2.5.1. Upgrade to get persistent task storage.

---

## Design Principles (Why We Built It This Way)

### No Cloud, Ever
Your journal contains your rawest thoughts. We believe that data should never cross a network boundary without your explicit, informed consent.

### No Hardcoded Psychology
We don't pretend to know what "stressed" or "motivated" looks like in every language and culture. We extract signals. The caller interprets them.

### Append-Only by Default
Writing should be frictionless. Deletion and archiving are intentional, slower operations.

### Backup Before Change
Every mutation creates a `.bak`. Accidents happen. We make them recoverable.

---

## Version

**Current**: `2.5.2`

**Requirements**:
- Python 3.9+
- Unix/Linux/Mac (uses `fcntl` for file locking)

**License**: Same as OPC200 project

---

*"The best journal is the one you actually write in."*
