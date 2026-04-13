# Architecture Decision Records

## ADR-001: Local-Only Architecture

**Date**: 2024-03-21  
**Status**: Accepted  
**Decision**: All OPC skills are strictly local-only with no external network calls.

**Rationale**: Privacy-first design ensures user data never leaves the local environment.

**Consequences**: Skills cannot use cloud services, all data must be stored locally.

---

## ADR-002: LLM-First Interpretation Layer (v2.5.1)

**Date**: 2026-04-13  
**Status**: Accepted  
**Decision**: Remove all hardcoded semantic interpretation from commands. Commands act as data layers returning structural signals and context for the caller (LLM) to interpret dynamically.

### Affected Commands

| Command | Previous Behavior | v2.5.1 Behavior |
|---------|------------------|-----------------|
| `record` | Hardcoded emotion analysis via keywords | Returns raw content; emotion only if caller provides it |
| `analyze` | Pre-baked emotional/work/decision interpretations | Returns structural signals (punctuation, caps, quotes) plus minimal keyword fragments (action/challenge/achievement regex matches) |
| `insights` | Fixed theme/recommendation pairs | Returns raw context + signal counts (structural + keyword-based) |
| `milestones` | Keyword-based milestone detection | Returns raw candidate object |
| `status` | Generated status messages | Returns raw statistics |

### Rationale

1. **Language Agnostic**: Hardcoded English interpretations failed for Chinese, Japanese, and other languages. Structural signals work everywhere.
2. **Flexibility**: LLM can adapt interpretation based on full context, not just local patterns.
3. **Maintainability**: No need to update complex interpretation logic as language evolves.
4. **Honesty**: `analyze` and `insights` use minimal keyword regex patterns for quick context extraction. This is lightweight semantic extraction, not "zero semantic processing." Emotional and psychological interpretation is fully delegated to the caller.

### Consequences

- Commands return more data, not conclusions
- Callers (LLM) must perform interpretation
- Better multi-language support without i18n complexity
- More network-efficient (full text + signals vs. pre-computed interpretations)

---

## ADR-003: File Locking for Concurrency

**Date**: 2026-04-13  
**Status**: Accepted  
**Decision**: Use `fcntl.flock()` for POSIX-compliant file locking on metadata and task storage.

### Implementation

- `journal_meta.json`: Shared lock (LOCK_SH) for reads, exclusive lock (LOCK_EX) for writes
- `tasks.json`: Same locking strategy
- All writes followed by `fsync()` for durability

### Rationale

Prevents race conditions when multiple commands execute simultaneously.

### Consequences

- Unix/Linux/Mac only (fcntl not available on Windows)
- Slight performance overhead (microseconds)
- Single-writer scalability limit acceptable for personal journaling

---

## ADR-004: Timezone-Aware Datetimes

**Date**: 2026-04-13  
**Status**: Accepted  
**Decision**: All datetime operations use explicit `Asia/Shanghai` timezone via `zoneinfo`.

### Implementation

```python
from utils.timezone import now_tz
now = now_tz()  # Always returns Asia/Shanghai aware datetime
```

### Rationale

- Consistent timestamps across DST changes
- Explicit timezone prevents ambiguity
- Matches user preference (Danny's timezone)

### Consequences

- Requires Python 3.9+ (zoneinfo)
- Cannot rely on naive datetime comparisons

---

## ADR-005: Entry Block Parsing

**Date**: 2026-04-13  
**Status**: Accepted  
**Decision**: Use centralized `utils/parsing.py` for entry block extraction to ensure consistent separator handling.

### Format

Entries are separated by:
```markdown

---
type: entry
```

### Implementation

- `split_entries()`: Split file content into blocks
- `join_entries()`: Reconstruct file from blocks preserving separators
- `extract_entries()`: Parse blocks into structured data

### Rationale

- Prevents separator loss bugs during deletions
- DRY principle: one parsing implementation for search, export, delete
- Easier to extend parsing logic (e.g., new frontmatter fields)

---

## ADR-006: Task Persistence

**Date**: 2026-04-13  
**Status**: Accepted  
**Decision**: Tasks created via `task` and `batch-task` are persisted to `tasks.json` with full CRUD operations.

### Storage Model

```
customers/{cid}/tasks.json
```

### Rationale

Previous implementation stored tasks only in memory, lost on restart.

### Consequences

- Tasks survive process restarts
- CRUD operations available via `task_storage.py`
- File locking required for concurrent access
