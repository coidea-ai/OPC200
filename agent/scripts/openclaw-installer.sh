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

custom_provider_api() {
  local c
  c="$(echo -n "${OPENCLAW_CUSTOM_COMPATIBILITY:-openai}" | tr '[:upper:]' '[:lower:]')"
  case "$c" in
    anthropic*) echo "anthropic-messages" ;;
    *) echo "openai-completions" ;;
  esac
}

safe_provider_id() {
  local r="${1:-custom}"
  r="$(echo -n "$r" | tr '[:upper:]' '[:lower:]' | tr '.' '-')"
  if [[ ! "$r" =~ ^[a-z][a-z0-9_-]*$ ]]; then
    echo "custom"
  else
    echo "$r"
  fi
}

run_onboard() {
  step "2/4 模型配置（config + models）"
  ensure_openclaw
  local auth="$OPENCLAW_AUTH_CHOICE"
  if [[ -z "$auth" && "$SILENT" == false ]]; then
    echo "1) apiKey  2) openai-api-key  3) gemini-api-key  4) custom-api-key"
    local pick=""
    read -r -p "选择 [1-4]: " pick
    case "$pick" in
      1) auth="apiKey" ;;
      2) auth="openai-api-key" ;;
      3) auth="gemini-api-key" ;;
      4) auth="custom-api-key" ;;
      *) die "无效选择" ;;
    esac
  fi
  [[ -n "$auth" ]] || die "静默模式需 --openclaw-auth-choice 或 OPENCLAW_AUTH_CHOICE"

  if [[ "$auth" == "custom-api-key" ]]; then
    [[ -n "${OPENCLAW_CUSTOM_BASE_URL:-}" ]] || OPENCLAW_CUSTOM_BASE_URL="$(read_required OPENCLAW_CUSTOM_BASE_URL)"
    [[ -n "${OPENCLAW_CUSTOM_MODEL_ID:-}" ]] || OPENCLAW_CUSTOM_MODEL_ID="$(read_required OPENCLAW_CUSTOM_MODEL_ID)"
    [[ -n "${CUSTOM_API_KEY:-}" ]] || CUSTOM_API_KEY="$(read_required CUSTOM_API_KEY)"
    export OPENCLAW_CUSTOM_BASE_URL OPENCLAW_CUSTOM_MODEL_ID CUSTOM_API_KEY
    local api_mode pid base mid ref_key prov_json allow_json
    api_mode="$(custom_provider_api)"
    pid="$(safe_provider_id "${OPENCLAW_CUSTOM_PROVIDER_ID:-custom}")"
    base="${OPENCLAW_CUSTOM_BASE_URL// /}"
    base="${base%/}"
    mid="${OPENCLAW_CUSTOM_MODEL_ID// /}"
    ref_key="${pid}/${mid}"
    prov_json="$(python3 -c 'import json,sys; b,a,m=sys.argv[1:4]; print(json.dumps({"baseUrl":b,"api":a,"apiKey":"${CUSTOM_API_KEY}","models":[{"id":m,"name":m}]}))' \
      "$base" "$api_mode" "$mid")"
    openclaw config set models.mode merge || warn "config set models.mode merge 非 0，继续"
    openclaw config set "models.providers.${pid}" "$prov_json" --strict-json || die "openclaw config set models.providers 失败"
    openclaw config set "agents.defaults.models[\"${ref_key}\"]" "{}" --strict-json || die "openclaw config set agents.defaults.models 失败"
    openclaw config set agents.defaults.model.primary "$ref_key" || die "openclaw config set agents.defaults.model.primary 失败"
    openclaw models set "$ref_key" || die "openclaw models set 失败"
  else
    case "$auth" in
      apiKey)
        if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
          read -r -p "ANTHROPIC_API_KEY: " ANTHROPIC_API_KEY
          export ANTHROPIC_API_KEY
        fi
        [[ -n "${ANTHROPIC_API_KEY:-}" ]] || die "需要 ANTHROPIC_API_KEY"
        ;;
      openai-api-key)
        if [[ -z "${OPENAI_API_KEY:-}" ]]; then
          read -r -p "OPENAI_API_KEY: " OPENAI_API_KEY
          export OPENAI_API_KEY
        fi
        [[ -n "${OPENAI_API_KEY:-}" ]] || die "需要 OPENAI_API_KEY"
        ;;
      gemini-api-key)
        if [[ -z "${GEMINI_API_KEY:-}" ]]; then
          read -r -p "GEMINI_API_KEY: " GEMINI_API_KEY
          export GEMINI_API_KEY
        fi
        [[ -n "${GEMINI_API_KEY:-}" ]] || die "需要 GEMINI_API_KEY"
        ;;
      *) die "不支持的 OPENCLAW_AUTH_CHOICE: $auth" ;;
    esac
    local def mr
    case "$auth" in
      apiKey) def="anthropic/claude-sonnet-4-5" ;;
      openai-api-key) def="openai/gpt-4.1" ;;
      *) def="google/gemini-2.5-flash" ;;
    esac
    mr="${OPENCLAW_MODEL_REF:-$def}"
    if [[ "$SILENT" == false ]]; then
      read -r -p "模型 provider/model [回车=$mr]: " _mr
      if [[ -n "$_mr" ]]; then
        mr="$_mr"
      fi
    fi
    openclaw config set "agents.defaults.models[\"${mr}\"]" "{}" --strict-json || warn "agents.defaults.models[…] 非 0，继续"
    openclaw config set agents.defaults.model.primary "$mr" || die "openclaw config set agents.defaults.model.primary 失败"
    openclaw models set "$mr" || die "openclaw models set 失败"
  fi
  openclaw config validate || warn "openclaw config validate 非 0，请检查 openclaw.json"
  openclaw models status || true
  ok "模型配置完成（config + models）"
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
