#!/usr/bin/env bash
set -euo pipefail

SILENT=false
OPENCLAW_AUTH_CHOICE="${OPENCLAW_AUTH_CHOICE:-}"
GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --silent) SILENT=true; shift ;;
    --openclaw-auth-choice) OPENCLAW_AUTH_CHOICE="$2"; shift 2 ;;
    --gateway-port) GATEWAY_PORT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$SCRIPT_DIR/openclaw-releases"
TEMPLATES_DIR="$SCRIPT_DIR/openclaw-templates"
OPENCLAW_SKILLS_DIR="$SCRIPT_DIR/openclaw-skills"
OPENCLAW_SKILLS_ZIP="${OPENCLAW_SKILLS_DIR}/skills.zip"
DMG_PATH="${RELEASE_DIR}/OpenClaw-2026.4.15.dmg"
DEFAULT_SKILLS="skill-vetter"

step() { echo "[STEP] $*"; }
ok() { echo "  [OK] $*"; }
warn() { echo " [WARN] $*" >&2; }
die() { echo "  [ERR] $*" >&2; exit 1; }

read_required() {
  local p="$1"
  local v=""
  while [[ -z "$v" ]]; do
    read -r -p "$p: " v
  done
  printf '%s' "$v"
}

ensure_openclaw() {
  command -v openclaw >/dev/null 2>&1 || die "未找到 openclaw 命令"
}

install_openclaw_macos() {
  step "1/4 安装 OpenClaw（内置 Release）"
  [[ "$(uname -s)" == "Darwin" ]] || die "该脚本仅用于 macOS"
  [[ -f "$DMG_PATH" ]] || die "未找到内置 macOS 资产: $DMG_PATH"
  local mount_point
  mount_point="$(mktemp -d)"
  hdiutil attach "$DMG_PATH" -mountpoint "$mount_point" -nobrowse >/dev/null
  if [[ ! -d "$mount_point/OpenClaw.app" ]]; then
    hdiutil detach "$mount_point" >/dev/null || true
    die "dmg 中未找到 OpenClaw.app"
  fi
  cp -R "$mount_point/OpenClaw.app" "/Applications/OpenClaw.app"
  hdiutil detach "$mount_point" >/dev/null || true
  if [[ -x "/Applications/OpenClaw.app/Contents/MacOS/OpenClaw" ]]; then
    export PATH="/Applications/OpenClaw.app/Contents/MacOS:$PATH"
  fi
  ok "OpenClaw.app 已安装到 /Applications"
}

moonshot_base_url() {
  case "${OPENCLAW_MOONSHOT_REGION:-cn}" in
    intl|global|international) echo "https://api.moonshot.ai/v1" ;;
    *) echo "https://api.moonshot.cn/v1" ;;
  esac
}

run_onboard() {
  step "2/4 模型配置（Kimi，config + models）"
  ensure_openclaw
  local kimi_ref="moonshot/kimi-k2.5"
  local prov_json base_url
  if [[ "$SILENT" == true ]]; then
    [[ -n "${MOONSHOT_API_KEY:-}" ]] || die "静默模式须设置环境变量 MOONSHOT_API_KEY"
  else
    if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
      read -r -p "Kimi (Moonshot) API Key（见 platform.moonshot.cn）: " MOONSHOT_API_KEY
      export MOONSHOT_API_KEY
    fi
    [[ -n "${MOONSHOT_API_KEY:-}" ]] || die "需要 MOONSHOT_API_KEY"
    if [[ -n "${OPENCLAW_MOONSHOT_REGION:-}" ]]; then
      ok "已用 OPENCLAW_MOONSHOT_REGION 选择 Moonshot 区域"
    else
      read -r -p "使用国际区 api.moonshot.ai？留空/回车=中国区 api.moonshot.cn [y/N]: " _reg
      _r="$(printf '%s' "$_reg" | tr '[:upper:]' '[:lower:]')"
      if [[ "$_r" == "y" || "$_r" == "yes" ]]; then
        export OPENCLAW_MOONSHOT_REGION="intl"
      else
        export OPENCLAW_MOONSHOT_REGION="cn"
      fi
    fi
  fi
  if [[ "$SILENT" == true && -z "${OPENCLAW_MOONSHOT_REGION:-}" ]]; then
    export OPENCLAW_MOONSHOT_REGION="cn"
  fi
  base_url="$(moonshot_base_url)"
  openclaw config set models.mode merge || warn "config set models.mode merge 非 0，继续"
  batch_f="$(mktemp "${TMPDIR:-/tmp}/oc-moon.XXXXXX.json")" || die "mktemp 失败"
  export MSH_BASE_URL="$base_url"
  python3 <<'PY' >"$batch_f"
import json, os
base = os.environ["MSH_BASE_URL"]
val = {
    "baseUrl": base,
    "api": "openai-completions",
    "apiKey": "${MOONSHOT_API_KEY}",
    "models": [
        {
            "id": "kimi-k2.5",
            "name": "Kimi K2.5",
            "reasoning": False,
            "input": ["text", "image"],
            "cost": {"input": 0.6, "output": 3, "cacheRead": 0.1, "cacheWrite": 0},
            "contextWindow": 262144,
            "maxTokens": 262144,
            "api": "openai-completions",
        }
    ],
}
print(json.dumps([{"path": "models.providers.moonshot", "value": val}]))
PY
  unset MSH_BASE_URL
  openclaw config set --batch-file "$batch_f" || die "openclaw config set --batch-file（models.providers.moonshot）失败"
  rm -f "$batch_f"
  openclaw config set "agents.defaults.models[\"${kimi_ref}\"]" "{}" --strict-json || die "openclaw config set agents.defaults.models 失败"
  openclaw config set agents.defaults.model.primary "$kimi_ref" || die "openclaw config set agents.defaults.model.primary 失败"
  openclaw models set "$kimi_ref" || die "openclaw models set 失败"
  openclaw config validate || warn "openclaw config validate 非 0，请检查 openclaw.json"
  openclaw models status || true
  ok "Kimi 模型已配置: $kimi_ref（$base_url）"
}

preinstall_assets() {
  step "3/4 轻预装（tools/skills/docs）"
  ensure_openclaw
  openclaw config set tools.profile full || warn "tools.profile 设置失败"
  # 旧逻辑封存：在线安装 skills（openclaw skills install）
  # openclaw skills install "$DEFAULT_SKILLS" || warn "skills 安装失败: $DEFAULT_SKILLS"
  local profile_dir="${OPENCLAW_PROFILE_DIR:-$HOME/.openclaw}"
  mkdir -p "$profile_dir"
  [[ -f "$OPENCLAW_SKILLS_ZIP" ]] || die "未找到内置 skills 资源包: $OPENCLAW_SKILLS_ZIP"
  local skills_dir="${profile_dir}/skills"
  mkdir -p "$skills_dir"
  if command -v unzip >/dev/null 2>&1; then
    unzip -o -q "$OPENCLAW_SKILLS_ZIP" -d "$skills_dir"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$OPENCLAW_SKILLS_ZIP" "$skills_dir" <<'PY'
import sys, zipfile
zip_path, target = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(target)
PY
  else
    die "缺少 unzip/python3，无法解压 skills 资源包"
  fi
  ok "skills 已解压到: $skills_dir"
  for name in AGENTS.md IDENTITY.md SOUL.md; do
    local src="$TEMPLATES_DIR/$name"
    local dst="$profile_dir/$name"
    if [[ -f "$src" ]]; then
      if [[ -f "$dst" ]]; then
        cp "$src" "${dst}.new"
      else
        cp "$src" "$dst"
      fi
    fi
  done
  ok "轻预装完成"
}

configure_gateway() {
  step "4/4 网关配置与验证"
  ensure_openclaw
  openclaw config set gateway.mode local
  openclaw config set gateway.tls.enabled false || true
  openclaw gateway install --port "$GATEWAY_PORT" || true
  openclaw gateway restart || openclaw gateway start || true
  sleep 2
  if ! openclaw gateway status --json --require-rpc >/dev/null 2>&1; then
    warn "网关未就绪，执行 doctor 诊断"
    openclaw doctor --non-interactive || true
    openclaw gateway restart || true
    sleep 2
    openclaw gateway status --json --require-rpc >/dev/null 2>&1 || die "网关启动失败，请检查 doctor 输出"
  fi
  ok "OpenClaw 安装完成: http://127.0.0.1:${GATEWAY_PORT}"
}

install_openclaw_macos
run_onboard
preinstall_assets
configure_gateway
