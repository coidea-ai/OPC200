#!/usr/bin/env bash
# 在仓库根目录生成与 install.sh 下载名一致的 Linux 单文件二进制（需 Python 3.10+、PyInstaller）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT"

ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
    x86_64|amd64)   OUT_NAME="opc-agent-linux-amd64" ;;
    aarch64|arm64)  OUT_NAME="opc-agent-linux-arm64" ;;
    *) echo "unsupported arch: $ARCH_RAW" >&2; exit 1 ;;
esac

VENV="$REPO_ROOT/.venv-opc-build"
if [[ ! -x "$VENV/bin/python" ]]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements-agent-binary.txt"

"$VENV/bin/pyinstaller" --noconfirm --clean --onefile \
    --name "$OUT_NAME" \
    --paths "$REPO_ROOT" \
    --hidden-import agent.src.exporter.collector \
    --hidden-import agent.src.exporter.pusher \
    --hidden-import yaml \
    --collect-submodules agent.src \
    --exclude-module agent.src.tests \
    --exclude-module pytest \
    "$REPO_ROOT/agent/src/opc_agent/cli.py"

echo "Done: $REPO_ROOT/dist/$OUT_NAME"
echo "安装: sudo $SCRIPT_DIR/install.sh --local-binary \"$REPO_ROOT/dist/$OUT_NAME\" ..."
