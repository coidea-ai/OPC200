#!/usr/bin/env python3
"""Check commit message format for Conventional Commits.

Usage:
    python check_commit_msg.py <commit-msg-file>

Exit codes:
    0 - Valid commit message
    1 - Invalid commit message

Reference:
    https://www.conventionalcommits.org/
"""
import re
import sys
from typing import Tuple

# Conventional Commits types
VALID_TYPES = [
    "feat",      # New feature
    "fix",       # Bug fix
    "docs",      # Documentation only
    "style",     # Code style (formatting, semicolons, etc.)
    "refactor",  # Code refactoring
    "perf",      # Performance improvements
    "test",      # Adding or correcting tests
    "build",     # Build system or dependencies
    "ci",        # CI/CD changes
    "chore",     # Other changes (maintenance)
    "revert",    # Reverting changes
]

# Regex patterns
HEADER_PATTERN = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[\w-]+)\))?(?P<breaking>!)?:(?P<subject>.+)$"
)

# Maximum lengths
MAX_HEADER_LENGTH = 72
MAX_BODY_LINE_LENGTH = 100


def check_commit_message(msg: str) -> Tuple[bool, str]:
    """Check if commit message follows Conventional Commits format.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    lines = msg.strip().split("\n")
    
    if not lines or not lines[0].strip():
        return False, "Commit message cannot be empty"
    
    header = lines[0].strip()
    
    # Check header length
    if len(header) > MAX_HEADER_LENGTH:
        return False, f"Header too long ({len(header)} > {MAX_HEADER_LENGTH}): {header}"
    
    # Check header format
    match = HEADER_PATTERN.match(header)
    if not match:
        return False, (
            f"Invalid commit message format: '{header}'\n"
            f"Expected format: <type>[(scope)][!]: <subject>\n"
            f"Valid types: {', '.join(VALID_TYPES)}\n"
            f"Examples:\n"
            f"  feat: add user authentication\n"
            f"  fix(api): resolve null pointer exception\n"
            f"  feat(skills)!: breaking change in journal API"
        )
    
    commit_type = match.group("type")
    subject = match.group("subject").strip()
    
    # Check type
    if commit_type not in VALID_TYPES:
        return False, (
            f"Invalid commit type: '{commit_type}'\n"
            f"Valid types: {', '.join(VALID_TYPES)}"
        )
    
    # Check subject is not empty
    if not subject:
        return False, "Commit subject cannot be empty"
    
    # Check subject starts with lowercase (optional convention)
    if subject[0].isupper():
        return False, f"Subject should start with lowercase: '{subject}'"
    
    # Check body line lengths (if any)
    if len(lines) > 2:
        for i, line in enumerate(lines[2:], start=3):
            if len(line) > MAX_BODY_LINE_LENGTH:
                return False, (
                    f"Body line {i} too long ({len(line)} > {MAX_BODY_LINE_LENGTH}): "
                    f"{line[:50]}..."
                )
    
    return True, ""


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: check_commit_msg.py <commit-msg-file>", file=sys.stderr)
        sys.exit(1)
    
    commit_msg_file = sys.argv[1]
    
    try:
        with open(commit_msg_file, "r", encoding="utf-8") as f:
            commit_msg = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {commit_msg_file}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Skip check for merge commits, revert commits, and squash messages
    if commit_msg.startswith(("Merge ", "Revert ", "Squash ")):
        print("✓ Skipping check for merge/revert/squash commit")
        sys.exit(0)
    
    is_valid, error_msg = check_commit_message(commit_msg)
    
    if is_valid:
        print("✓ Commit message format is valid")
        sys.exit(0)
    else:
        print(f"✗ Invalid commit message:\n{error_msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
