#!/usr/bin/env bash
set -euo pipefail
# Usage: build-agent-bundle.sh <version_semver> <output_parent_dir>
# Creates <output_parent_dir>/agent/ with minimal tree + stub agent/src/__init__.py

VERSION="${1:?version required}"
OUT_PARENT="${2:?output parent required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STAGE="$OUT_PARENT/agent"

rm -rf "$STAGE"
mkdir -p "$STAGE/src"

cp -a "$REPO_ROOT/agent/src/opc_agent" "$STAGE/src/"
cp -a "$REPO_ROOT/agent/src/exporter" "$STAGE/src/"
cp -a "$REPO_ROOT/agent/scripts" "$STAGE/scripts"

cat > "$STAGE/src/__init__.py" <<EOF
"""Minimal package root for standalone agent bundle (no monorepo src.* imports)."""
__version__ = "$VERSION"
EOF

printf '%s\n' '"""OPC200 agent bundle."""' > "$STAGE/__init__.py"
