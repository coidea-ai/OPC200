#!/usr/bin/env bash
set -euo pipefail

NODE_VERSION="24.15.0"
NODE_MAJOR=24
NODE_MIRROR="https://registry.npmmirror.com/-/binary/node"
GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
OPENCLAW_NPM_VERSION="${OPENCLAW_NPM_VERSION:-latest}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; GRAY='\033[0;90m'; NC='\033[0m'
step()  { printf "${CYAN}[STEP] %s${NC}\n" "$*"; }
ok()    { printf "${GREEN}  [OK] %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW} [WARN] %s${NC}\n" "$*"; }
fail()  { printf "${RED}  [ERR] %s${NC}\n" "$*"; exit 1; }

SPINNER_PID=""
spinner_start() {
  local msg="${1:-请稍候}"
  (
    local chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0 sec=0
    while true; do
      printf "\r${GRAY}  [%s] %s（已等待 %ds）…${NC}" "${chars:i%${#chars}:1}" "$msg" "$sec"
      sleep 0.3
      i=$((i+1))
      sec=$(( i * 3 / 10 ))
    done
  ) &
  SPINNER_PID=$!
}
spinner_stop() {
  if [[ -n "$SPINNER_PID" ]]; then
    kill "$SPINNER_PID" 2>/dev/null; wait "$SPINNER_PID" 2>/dev/null || true
    SPINNER_PID=""
    printf "\r\033[K"
  fi
}

# ── 1/5 环境检测 ──────────────────────────────────────────────

step "1/5 环境检测"

[[ "$(uname -s)" == "Darwin" ]] || fail "本脚本仅支持 macOS"
ok "操作系统: macOS"

ARCH="$(uname -m)"
case "$ARCH" in
  arm64|aarch64) NODE_ARCH="arm64" ;;
  x86_64)        NODE_ARCH="x64"   ;;
  *) fail "不支持的架构: $ARCH" ;;
esac
ok "架构: $ARCH (node-$NODE_ARCH)"

need_install_node=false
if command -v node &>/dev/null; then
  CUR_NODE="$(node -v 2>/dev/null || true)"
  CUR_MAJOR="$(echo "$CUR_NODE" | sed 's/^v//' | cut -d. -f1)"
  if [[ -n "$CUR_MAJOR" ]] && (( CUR_MAJOR >= NODE_MAJOR )); then
    ok "Node 版本: $CUR_NODE (>= v${NODE_MAJOR}，跳过安装)"
  else
    warn "Node 版本过低: $CUR_NODE，需要 >= v${NODE_MAJOR}，将在线安装 v${NODE_VERSION}"
    need_install_node=true
  fi
else
  warn "未检测到 Node，将在线安装 v${NODE_VERSION}"
  need_install_node=true
fi

if $need_install_node; then
  NODE_TAR="node-v${NODE_VERSION}-darwin-${NODE_ARCH}.tar.gz"
  NODE_URL="${NODE_MIRROR}/v${NODE_VERSION}/${NODE_TAR}"
  NODE_INSTALL_DIR="${HOME}/.local/node-v${NODE_VERSION}"

  step "1.1 在线安装 Node v${NODE_VERSION}"
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  printf "  下载中: %s\n" "$NODE_URL"
  curl -fSL --progress-bar -o "${TMP_DIR}/${NODE_TAR}" "$NODE_URL" \
    || fail "Node 下载失败，请检查网络或链接: $NODE_URL"

  rm -rf "$NODE_INSTALL_DIR"
  mkdir -p "$NODE_INSTALL_DIR"
  tar -xzf "${TMP_DIR}/${NODE_TAR}" -C "$NODE_INSTALL_DIR" --strip-components=1 \
    || fail "Node 解压失败"

  export PATH="${NODE_INSTALL_DIR}/bin:$PATH"

  SHELL_RC=""
  if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
  else
    SHELL_RC="$HOME/.bashrc"
  fi

  NODE_PATH_LINE="export PATH=\"${NODE_INSTALL_DIR}/bin:\$PATH\""
  if ! grep -qF "$NODE_INSTALL_DIR/bin" "$SHELL_RC" 2>/dev/null; then
    printf '\n# Node.js v%s (added by openclaw-installer)\n%s\n' "$NODE_VERSION" "$NODE_PATH_LINE" >> "$SHELL_RC"
    ok "已写入 PATH 到 $SHELL_RC"
  fi

  rm -rf "$TMP_DIR"
  trap - EXIT

  INSTALLED_NODE="$(node -v 2>/dev/null || true)"
  [[ "$INSTALLED_NODE" == "v${NODE_VERSION}" ]] || fail "Node 安装后版本不匹配: $INSTALLED_NODE"
  ok "Node 已安装: $INSTALLED_NODE"
fi

step "1.2 设置 npm 淘宝源"
npm config set registry https://registry.npmmirror.com/
ok "npm registry: $(npm config get registry)"

# ── 2/5 安装 OpenClaw ─────────────────────────────────────────

step "2/5 安装 OpenClaw"

if command -v openclaw &>/dev/null && OC_VER="$(openclaw --version 2>/dev/null | head -1)" && [[ -n "$OC_VER" ]]; then
  ok "OpenClaw 已安装: $OC_VER，跳过"
else
  printf "  正在通过 npm 安装 openclaw@%s …\n" "$OPENCLAW_NPM_VERSION"
  spinner_start "npm install openclaw"
  npm install -g "openclaw@${OPENCLAW_NPM_VERSION}" --no-audit --no-fund &>/dev/null \
    && npm_ok=true || npm_ok=false
  spinner_stop
  $npm_ok || fail "npm install -g openclaw 失败"
  command -v openclaw &>/dev/null || fail "安装后未找到 openclaw 命令，请检查 npm 全局 bin 是否在 PATH"
  ok "openclaw 命令可用"
fi

# ── 3/5 Onboard（非交互式，Kimi / Moonshot） ─────────────────

step "3/5 Onboard 新手引导（Moonshot Kimi）"

if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
  printf "  请输入 Kimi（Moonshot）API Key: "
  read -r MOONSHOT_API_KEY
  [[ -n "$MOONSHOT_API_KEY" ]] || fail "MOONSHOT_API_KEY 不能为空"
fi
export MOONSHOT_API_KEY

AUTH_CHOICE="moonshot-api-key-cn"
if [[ -n "${OPENCLAW_MOONSHOT_REGION:-}" ]]; then
  case "${OPENCLAW_MOONSHOT_REGION,,}" in
    intl|global|international) AUTH_CHOICE="moonshot-api-key" ;;
  esac
else
  printf "  使用国际区 api.moonshot.ai？留空/回车=中国区 api.moonshot.cn [y/N]: "
  read -r region_input
  case "${region_input,,}" in
    y|yes) AUTH_CHOICE="moonshot-api-key" ;;
  esac
fi
ok "Moonshot 区域: $AUTH_CHOICE"

spinner_start "openclaw onboard"
openclaw onboard --non-interactive \
  --mode local \
  --auth-choice "$AUTH_CHOICE" \
  --moonshot-api-key "$MOONSHOT_API_KEY" \
  --gateway-port "$GATEWAY_PORT" \
  --gateway-bind loopback \
  --install-daemon \
  --skip-skills \
  &>/dev/null && onboard_ok=true || onboard_ok=false
spinner_stop

if $onboard_ok; then
  ok "onboard 完成"
else
  warn "onboard 退出码非 0，将尝试手动配置网关"
fi

openclaw config set agents.defaults.model.primary "moonshot/kimi-k2.5" 2>/dev/null || true
ok "默认模型已设为 moonshot/kimi-k2.5"

# ── 4/5 网关健康检查 ──────────────────────────────────────────

step "4/5 网关健康检查"

gateway_healthy() {
  openclaw gateway status --require-rpc --json &>/dev/null && return 0
  for endpoint in "http://127.0.0.1:${GATEWAY_PORT}/health" "http://127.0.0.1:${GATEWAY_PORT}/"; do
    http_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$endpoint" 2>/dev/null || true)"
    [[ "$http_code" =~ ^[23] ]] && return 0
  done
  return 1
}

wait_gateway() {
  local max_attempts=${1:-15}
  local interval=${2:-4}
  for (( i=1; i<=max_attempts; i++ )); do
    gateway_healthy && return 0
    printf "  [..] 等待网关就绪（%d/%d，每 %ds 探测）…\n" "$i" "$max_attempts" "$interval"
    sleep "$interval"
  done
  return 1
}

if wait_gateway 10 3; then
  ok "网关已就绪"
else
  warn "网关未就绪，尝试手动安装/重启"
  openclaw gateway stop 2>/dev/null || true
  sleep 2
  openclaw gateway install --force --port "$GATEWAY_PORT" 2>/dev/null || true
  sleep 3
  openclaw gateway restart 2>/dev/null || true
  sleep 5
  if wait_gateway 12 5; then
    ok "网关已就绪（手动恢复）"
  else
    warn "网关启动失败。可手动执行: openclaw gateway stop && openclaw gateway install --force --port $GATEWAY_PORT && openclaw gateway restart"
  fi
fi

# ── 5/5 打开页面 ──────────────────────────────────────────────

step "5/5 获取 Dashboard 地址"

DASHBOARD_URL=""
dashboard_output="$(openclaw dashboard 2>/dev/null || true)"
if [[ -n "$dashboard_output" ]]; then
  DASHBOARD_URL="$(echo "$dashboard_output" | grep -oE 'https?://(127\.0\.0\.1|localhost)(:[0-9]+)?[^ ]*#token=[^ ]*' | head -1 || true)"
  if [[ -z "$DASHBOARD_URL" ]]; then
    DASHBOARD_URL="$(echo "$dashboard_output" | grep -oE 'https?://(127\.0\.0\.1|localhost)(:[0-9]+)?[^ ]*' | head -1 || true)"
  fi
fi
[[ -z "$DASHBOARD_URL" ]] && DASHBOARD_URL="http://127.0.0.1:${GATEWAY_PORT}"

printf "\n${GREEN}════════════════════════════════════════════════════════${NC}\n"
printf "${GREEN}  OpenClaw 安装完成！${NC}\n"
printf "${GREEN}  Dashboard: %s${NC}\n" "$DASHBOARD_URL"
printf "${GREEN}════════════════════════════════════════════════════════${NC}\n\n"

if command -v open &>/dev/null; then
  open "$DASHBOARD_URL" 2>/dev/null || true
  ok "已在浏览器中打开 Dashboard"
else
  printf "  请在浏览器中打开上述地址。\n"
fi
