# Architecture Decision: Should all commands live in one Python file? Does file count affect process overhead?

## Short answer

**Technically yes**, but maintainability would suffer. More importantly — **multi-process overhead has nothing to do with file count**; Python does not spawn extra processes just because there are more files.

---

## 1. Can we put all commands into a single file?

**Yes.** Nothing in Python prevents you from writing `init`, `record`, `search`, `export`, `analyze`, `milestones`, `insights`, `task`, and `status` all into one `commands.py`.

For example:

```python
# commands.py (monolithic version)
def cmd_init(customer_id, args): ...
def cmd_record(customer_id, args): ...
def cmd_search(customer_id, args): ...
# ... all 9 commands
```

Then in `main.py` you just map them with a dict:

```python
COMMANDS = {
    "init": cmd_init,
    "record": cmd_record,
    ...
}
```

### Why not do it?

| Dimension | Multi-file (current) | Single file |
|-----------|----------------------|-------------|
| **Git diff** | Change `analyze.py` and only analysis logic changes | Any command change diffs the whole file |
| **Parallel dev** | Multiple people can work on different commands without conflicts | High chance of merge conflicts |
| **Hot reload** | Reload one small module | Reload the entire monolith |
| **Readability** | Open a file and know exactly which feature you are reading | Scroll through a giant file to find logic |
| **Test granularity** | Import one command per test file | High coupling |

For an Agent skill with lightweight code, splitting files has zero runtime cost; the benefits are entirely in developer experience.

---

## 2. Would a single file avoid multi-process overhead?

**No, because multi-process overhead does not come from file count.**

### Python import process

When you write in `main.py`:

```python
from scripts.commands import init, record, analyze
```

The Python interpreter:
1. Finds `init.py`
2. Reads it → compiles to bytecode → executes it in the **current process**

All three files run inside the **same Python process**; no new processes are spawned.

### Where does real multi-process overhead come from?

If your skill is invoked via OpenClaw `sessions_spawn()`, or via `subprocess.run(["python", "scripts/main.py"])`, only then do you incur multi-process overhead.

| Invocation | Multi-process? | Overhead source |
|------------|----------------|-----------------|
| `import scripts.main` then `main()` | ❌ Single process | None |
| `subprocess.run(["python", "main.py"])` | ✅ Multi-process | OS fork/exec |
| `sessions_spawn()` (OpenClaw) | ✅ Multi-process | New isolated session |
| `multiprocessing.Process(target=main)` | ✅ Multi-process | OS fork + IPC |

**Conclusion**: Whether you split commands into 9 files or 1 file, as long as the invocation is `import + function call`, it is single process. If the invocation is `subprocess` or `sessions_spawn`, it is multi-process — **completely independent of how many `.py` files you have**.

---

## 3. Is there really zero benefit to a single file?

Not exactly. One hard-to-ignore benefit exists:

**Slightly lower I/O overhead at startup due to fewer imports.**

Reading one 10 KB file is theoretically faster than reading nine 1 KB files (fewer syscalls), but at the skill level this difference is typically **< 1 ms** and can be ignored.

---

## 4. Recommendation for the journal skill

**Keep the current multi-file structure; it is the better engineering decision.**

If in the future you have a hard requirement for a single file (e.g., some deployment constraint), you can add a build step:

```bash
# build.py — inline all commands/*.py into one monolithic journal.py
python build.py  # outputs dist/journal_single_file.py
```

Keep multi-file during development, and generate a single file for release. This gives you the best of both worlds.

---

## One-sentence summary

> **More files ≠ more processes. File count does not determine runtime cost; invocation method does. A single file is possible, but maintenance costs outweigh performance gains.**
