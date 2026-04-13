"""Journal command: search - actual local file search."""
import glob
import os
import re
from pathlib import Path

from utils.storage import build_customer_dir
from scripts.commands._meta import get_language


def run(customer_id: str, args: dict) -> dict:
    """Search journal entries locally in memory files."""
    query = args.get("query", "").strip()
    limit = args.get("limit", 10)
    case_sensitive = args.get("case_sensitive", False)
    
    lang = get_language(customer_id)
    base = os.path.expanduser(build_customer_dir(customer_id))
    memory_dir = os.path.join(base, "memory")
    
    if not os.path.exists(memory_dir):
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "query": query,
                "matches": [],
                "total_matches": 0,
                "language": lang,
            },
            "message": "No memory directory found",
        }
    
    files = sorted(glob.glob(os.path.join(memory_dir, "*.md")))
    matches = []
    
    flags = 0 if case_sensitive else re.IGNORECASE
    
    for f in files:
        content = Path(f).read_text(encoding="utf-8")
        
        # Skip if query provided and not found in content
        if query and not re.search(re.escape(query), content, flags):
            continue
        
        # Extract entries from the file
        entries = _extract_entries(content, f)
        
        for entry in entries:
            if query:
                # Search within entry body
                body = entry.get("body", "")
                match_positions = []
                for m in re.finditer(re.escape(query), body, flags):
                    match_positions.append({
                        "start": m.start(),
                        "end": m.end(),
                        "context": _get_context(body, m.start(), m.end())
                    })
                
                if match_positions:
                    entry["matches"] = match_positions
                    matches.append(entry)
            else:
                # No query - return all entries
                matches.append(entry)
    
    # Sort by date (newest first) and limit results
    matches.sort(key=lambda x: x.get("date", "00-00-00"), reverse=True)
    total = len(matches)
    matches = matches[:limit]
    
    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "query": query,
            "matches": matches,
            "total_matches": total,
            "returned": len(matches),
            "language": lang,
        },
        "message": f"Found {total} match(es)" if query else f"Found {total} entries",
    }


def _extract_entries(content: str, file_path: str) -> list:
    """Extract individual entries from memory file content."""
    entries = []
    
    # Split by entry separator
    separator = "\n\n---\ntype: entry"
    if separator not in content:
        separator = "---\ntype: entry"
    
    parts = content.split(separator)
    
    for idx, part in enumerate(parts):
        if idx == 0 and not part.strip().startswith("type: entry"):
            # First part might be charter or empty
            if "type: charter" in part:
                continue
            if not part.strip():
                continue
            block = part
        else:
            if idx > 0:
                block = "---\ntype: entry" + part
            else:
                block = part
        
        # Parse frontmatter
        entry = _parse_entry_block(block, file_path)
        if entry:
            entries.append(entry)
    
    return entries


def _parse_entry_block(block: str, file_path: str) -> dict:
    """Parse a single entry block to extract metadata and body."""
    lines = block.split("\n")
    frontmatter = {}
    in_frontmatter = False
    body_lines = []
    
    for i, line in enumerate(lines):
        if line.strip() == "---" and i == 0:
            in_frontmatter = True
            continue
        if in_frontmatter and line.strip() == "---":
            in_frontmatter = False
            continue
        
        if in_frontmatter:
            if ":" in line:
                key, val = line.split(":", 1)
                frontmatter[key.strip()] = val.strip()
        else:
            body_lines.append(line)
    
    body = "\n".join(body_lines).strip()
    
    # Skip if not an entry
    if frontmatter.get("type") != "entry":
        return None
    
    return {
        "entry_id": frontmatter.get("entry_id", ""),
        "date": frontmatter.get("date", ""),
        "day": frontmatter.get("day", ""),
        "type": frontmatter.get("type", ""),
        "emotion": frontmatter.get("emotion", ""),
        "file": file_path,
        "body": body,
    }


def _get_context(text: str, start: int, end: int, context_len: int = 40) -> str:
    """Get context around a match."""
    context_start = max(0, start - context_len)
    context_end = min(len(text), end + context_len)
    
    prefix = "..." if context_start > 0 else ""
    suffix = "..." if context_end < len(text) else ""
    
    return prefix + text[context_start:context_end] + suffix
