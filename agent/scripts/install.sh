#!/usr/bin/env bash
# AGENT-003: OPC200 Agent Mac/Linux 安装脚本 (v2)
# 按 AGENT-001 (docs/INSTALL_SCRIPT_SPEC.md) 规范实现
# 流程: 环境检查 → 配置获取 → 下载 Agent → 安装部署 → 注册服务 → 启动验证 → 完成输出

set -euo pipefail

# ── 常量 ──────────────────────────────────────────────────────────

AGENT_VERSION="2.3.0"
DOWNLOAD_BASE="https://github.com/coidea-ai/OPC200/releases/download/v${AGENT_VERSION}"
SERVICE_NAME="opc200-agent"
DEFAULT_URL="https://platform.opc200.co"
DEFAULT_PORT=8080
MIN_DISK_MB=1024

# 错误码 (AGENT-001 §6.1)
E001=1  # 权限不足
E002=2  # 网络连接失败
E003=3  # 端口占用
E004=4  # 校验失败
E005=5  # 服务注册失败

# ── 运行时变量 ────────────────────────────────────────────────────

PLATFORM_URL=""
CUSTOMER_ID=""
API_KEY=""
INSTALL_DIR=""
PORT="${DEFAULT_PORT}"
SILENT=false
OS_TYPE=""       # linux / darwin
ARCH=""          # amd64 / arm64
AGENT_BINARY=""
ROLLBACK_ITEMS=()

# ── 辅助函数 ──────────────────────────────────────────────────────

info()  { printf "\033[36m[STEP] %s\033[0m\n" "$*"; }
ok()    { printf "\033[32m  [OK] %s\033[0m\n" "$*"; }
warn()  { printf "\033[33m [WARN] %s\033[0m\n" "$*"; }
err()   { printf "\033[31m  [ERR] %s\033[0m\n" "$*"; }

fail() {
    local code=$1; shift
    err "$*"
    rollback
    exit "$code"
}

register_rollback() { ROLLBACK_ITEMS+=("$1"); }

rollback() {
    [[ ${#ROLLBACK_ITEMS[@]} -eq 0 ]] && return
    warn "正在回滚..."
    for (( i=${#ROLLBACK_ITEMS[@]}-1; i>=0; i-- )); do
        eval "${ROLLBACK_ITEMS[$i]}" 2>/dev/null || warn "回滚步骤失败: ${ROLLBACK_ITEMS[$i]}"
    done
}

detect_pkg_manager() {
    if command -v brew &>/dev/null; then
        ok "检测到包管理器: brew"
    elif command -v apt-get &>/dev/null; then
        ok "检测到包管理器: apt"
    elif command -v yum &>/dev/null; then
        ok "检测到包管理器: yum"
    elif command -v dnf &>/dev/null; then
        ok "检测到包管理器: dnf"
    elif command -v pacman &>/dev/null; then
        ok "检测到包管理器: pacman"
    else
        warn "未检测到常用包管理器"
    fi
}

# ── Step 1: 环境检查 ─────────────────────────────────────────────

step_check_env() {
    info "1/7 环境检查"

    # root / sudo
    if [[ $EUID -ne 0 ]]; then
        fail $E001 "E001: 请以 root 或 sudo 运行此脚本"
    fi
    ok "root 权限"

    # OS
    OS_TYPE="$(uname -s | tr '[:upper:]' '[:lower:]')"
    case "$OS_TYPE" in
        linux)
            if [[ -f /etc/os-release ]]; then
                . /etc/os-release
                ok "Linux: ${PRETTY_NAME:-$ID}"
            else
                ok "Linux"
            fi
            ;;
        darwin)
            local mac_ver
            mac_ver="$(sw_vers -productVersion 2>/dev/null || echo "unknown")"
            local major="${mac_ver%%.*}"
            if [[ "$major" != "unknown" ]] && [[ "$major" -lt 12 ]]; then
                fail $E001 "E001: 需要 macOS 12+（当前 $mac_ver）"
            fi
            ok "macOS $mac_ver"
            ;;
        *)
            fail $E001 "E001: 不支持的操作系统: $OS_TYPE"
            ;;
    esac

    # 架构
    local machine
    machine="$(uname -m)"
    case "$machine" in
        x86_64|amd64)   ARCH="amd64" ;;
        aarch64|arm64)  ARCH="arm64" ;;
        *)              fail $E001 "E001: 不支持的架构: $machine" ;;
    esac
    ok "架构: $ARCH"

    AGENT_BINARY="opc-agent-${OS_TYPE}-${ARCH}"

    # 磁盘
    local free_mb
    if [[ "$OS_TYPE" == "darwin" ]]; then
        free_mb=$(df -m / | awk 'NR==2{print $4}')
    else
        free_mb=$(df -m / | awk 'NR==2{print $4}')
    fi
    if [[ "$free_mb" -lt "$MIN_DISK_MB" ]]; then
        fail $E001 "E001: 磁盘可用 ${free_mb}MB，需要 ${MIN_DISK_MB}MB+"
    fi
    ok "磁盘可用 ${free_mb}MB"

    # 端口
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
            fail $E003 "E003: 端口 $PORT 被占用"
        fi
    elif command -v lsof &>/dev/null; then
        if lsof -iTCP:"$PORT" -sTCP:LISTEN &>/dev/null; then
            fail $E003 "E003: 端口 $PORT 被占用"
        fi
    fi
    ok "端口 $PORT 可用"

    detect_pkg_manager
}

# ── Step 2: 获取配置 ─────────────────────────────────────────────

step_get_config() {
    info "2/7 获取配置"

    if $SILENT; then
        [[ -z "$PLATFORM_URL" ]] && PLATFORM_URL="$DEFAULT_URL"
        [[ -z "$CUSTOMER_ID" ]] && fail $E001 "E001: 静默模式必须提供 --customer-id"
        [[ -z "$API_KEY" ]]     && fail $E001 "E001: 静默模式必须提供 --api-key"
    else
        local input
        read -rp "平台地址 [${DEFAULT_URL}]: " input
        PLATFORM_URL="${input:-$DEFAULT_URL}"

        while [[ -z "$CUSTOMER_ID" ]]; do
            read -rp "Customer ID (必需): " CUSTOMER_ID
            [[ -z "$CUSTOMER_ID" ]] && err "Customer ID 不能为空"
        done

        while [[ -z "$API_KEY" ]]; do
            read -rsp "API Key (必需): " API_KEY
            echo
            [[ -z "$API_KEY" ]] && err "API Key 不能为空"
        done
    fi

    [[ -z "$INSTALL_DIR" ]] && INSTALL_DIR="$HOME/.opc200"

    ok "平台: $PLATFORM_URL"
    ok "用户: $CUSTOMER_ID"
    ok "目录: $INSTALL_DIR"
}

# ── Step 3: 下载 Agent ───────────────────────────────────────────

step_download() {
    info "3/7 下载 Agent"

    local bin_url="${DOWNLOAD_BASE}/${AGENT_BINARY}"
    local sha_url="${DOWNLOAD_BASE}/SHA256SUMS"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    local bin_dest="${tmp_dir}/${AGENT_BINARY}"
    local sha_dest="${tmp_dir}/SHA256SUMS"

    local dl_cmd=""
    if command -v curl &>/dev/null; then
        dl_cmd="curl"
    elif command -v wget &>/dev/null; then
        dl_cmd="wget"
    else
        fail $E002 "E002: 需要 curl 或 wget"
    fi

    if [[ "$dl_cmd" == "curl" ]]; then
        curl -fSL --connect-timeout 30 -o "$bin_dest" "$bin_url" || fail $E002 "E002: 下载失败 - $bin_url"
    else
        wget -q --timeout=30 -O "$bin_dest" "$bin_url" || fail $E002 "E002: 下载失败 - $bin_url"
    fi
    ok "已下载 $AGENT_BINARY"

    # SHA256 校验
    if [[ "$dl_cmd" == "curl" ]]; then
        curl -fSL --connect-timeout 10 -o "$sha_dest" "$sha_url" 2>/dev/null
    else
        wget -q --timeout=10 -O "$sha_dest" "$sha_url" 2>/dev/null
    fi

    if [[ -f "$sha_dest" ]]; then
        local expected
        expected="$(grep "$AGENT_BINARY" "$sha_dest" 2>/dev/null | awk '{print $1}')"
        if [[ -n "$expected" ]]; then
            local actual
            if command -v sha256sum &>/dev/null; then
                actual="$(sha256sum "$bin_dest" | awk '{print $1}')"
            elif command -v shasum &>/dev/null; then
                actual="$(shasum -a 256 "$bin_dest" | awk '{print $1}')"
            fi
            if [[ -n "${actual:-}" ]]; then
                if [[ "$actual" != "$expected" ]]; then
                    fail $E004 "E004: SHA256 校验失败（期望 $expected，实际 $actual）"
                fi
                ok "SHA256 校验通过"
            else
                warn "无 sha256sum/shasum，跳过校验"
            fi
        else
            warn "SHA256SUMS 中未找到对应条目，跳过校验"
        fi
    else
        warn "无法下载 SHA256SUMS，跳过校验"
    fi

    TMP_BINARY="$bin_dest"
}

# ── Step 4: 安装部署 ─────────────────────────────────────────────

step_install() {
    info "4/7 安装部署"

    local root="$INSTALL_DIR"
    local dirs=("$root" "$root/bin" "$root/config" "$root/data" "$root/data/exporter" "$root/logs")

    for d in "${dirs[@]}"; do
        mkdir -p "$d"
    done
    register_rollback "rm -rf '$root'"
    ok "目录结构已创建"

    cp "$TMP_BINARY" "$root/bin/opc-agent"
    chmod +x "$root/bin/opc-agent"
    ok "Agent 二进制已部署"

    # config.yml (AGENT-001 §3.2)
    cat > "$root/config/config.yml" <<YAML
platform:
  url: "${PLATFORM_URL}"
  metrics_endpoint: "/metrics/job"

customer:
  id: "${CUSTOMER_ID}"

agent:
  version: "${AGENT_VERSION}"
  check_interval: 60
  push_interval: 30

gateway:
  host: "127.0.0.1"
  port: ${PORT}


logging:
  level: "info"
  file: "${root}/logs/agent.log"
  max_size: "100MB"
  max_backups: 5
YAML
    ok "config.yml 已写入"

    # .env (权限 600)
    printf 'OPC200_API_KEY=%s\n' "$API_KEY" > "$root/.env"
    chmod 600 "$root/.env"
    ok ".env 已写入（权限 600）"
}

# ── Step 5: 注册系统服务 ─────────────────────────────────────────

step_register_service() {
    info "5/7 注册系统服务"

    local agent_bin="${INSTALL_DIR}/bin/opc-agent"
    local config_yml="${INSTALL_DIR}/config/config.yml"

    if [[ "$OS_TYPE" == "linux" ]]; then
        _register_systemd "$agent_bin" "$config_yml"
    elif [[ "$OS_TYPE" == "darwin" ]]; then
        _register_launchd "$agent_bin" "$config_yml"
    fi
}

_register_systemd() {
    local agent_bin="$1" config_yml="$2"
    local unit_path="/etc/systemd/system/${SERVICE_NAME}.service"

    cat > "$unit_path" <<UNIT
[Unit]
Description=OPC200 Agent Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${agent_bin} --config ${config_yml} service run
Restart=on-failure
RestartSec=5
StandardOutput=append:${INSTALL_DIR}/logs/agent.log
StandardError=append:${INSTALL_DIR}/logs/agent.log

[Install]
WantedBy=multi-user.target
UNIT

    register_rollback "systemctl disable ${SERVICE_NAME} 2>/dev/null; rm -f '${unit_path}'"

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" || fail $E005 "E005: systemd enable 失败"
    ok "systemd 服务已注册（${unit_path}）"
}

_register_launchd() {
    local agent_bin="$1" config_yml="$2"
    local plist_path="${HOME}/Library/LaunchAgents/co.opc200.agent.plist"

    mkdir -p "${HOME}/Library/LaunchAgents"

    cat > "$plist_path" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>co.opc200.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${agent_bin}</string>
        <string>--config</string>
        <string>${config_yml}</string>
        <string>service</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${INSTALL_DIR}/logs/agent.log</string>
    <key>StandardErrorPath</key>
    <string>${INSTALL_DIR}/logs/agent.log</string>
</dict>
</plist>
PLIST

    register_rollback "launchctl unload '${plist_path}' 2>/dev/null; rm -f '${plist_path}'"
    ok "launchd plist 已写入（${plist_path}）"
}

# ── Step 6: 启动验证 ─────────────────────────────────────────────

step_start_verify() {
    info "6/7 启动验证"

    if [[ "$OS_TYPE" == "linux" ]]; then
        systemctl start "$SERVICE_NAME" || fail $E005 "E005: 服务启动失败"
        ok "systemd 服务已启动"
    elif [[ "$OS_TYPE" == "darwin" ]]; then
        local plist_path="${HOME}/Library/LaunchAgents/co.opc200.agent.plist"
        launchctl load "$plist_path" 2>/dev/null || fail $E005 "E005: launchctl load 失败"
        ok "launchd 服务已加载"
    fi

    # 健康检查
    local health_url="http://127.0.0.1:${PORT}/health"
    local healthy=false
    for i in $(seq 1 10); do
        if command -v curl &>/dev/null; then
            if curl -sf --connect-timeout 2 "$health_url" &>/dev/null; then
                healthy=true; break
            fi
        elif command -v wget &>/dev/null; then
            if wget -q --timeout=2 -O /dev/null "$health_url" 2>/dev/null; then
                healthy=true; break
            fi
        fi
        sleep 2
    done

    if $healthy; then
        ok "健康检查通过（$health_url）"
    else
        warn "健康检查超时，Agent 可能仍在启动中"
    fi
}

# ── Step 7: 完成输出 ─────────────────────────────────────────────

step_summary() {
    info "7/7 安装完成"

    echo ""
    echo "  安装目录 : $INSTALL_DIR"
    echo "  配置文件 : $INSTALL_DIR/config/config.yml"
    echo "  日志文件 : $INSTALL_DIR/logs/agent.log"
    echo "  健康检查 : http://127.0.0.1:${PORT}/health"
    echo ""

    if [[ "$OS_TYPE" == "linux" ]]; then
        echo "  查看状态 : systemctl status $SERVICE_NAME"
        echo "  查看日志 : journalctl -u $SERVICE_NAME -f"
        echo "  卸载     : sudo ./uninstall.sh --install-dir '$INSTALL_DIR'"
    elif [[ "$OS_TYPE" == "darwin" ]]; then
        echo "  查看日志 : tail -f $INSTALL_DIR/logs/agent.log"
        echo "  卸载     : ./uninstall.sh --install-dir '$INSTALL_DIR'"
    fi
    echo ""
}

# ── 参数解析 ──────────────────────────────────────────────────────

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --platform-url)  PLATFORM_URL="$2"; shift 2 ;;
            --customer-id)   CUSTOMER_ID="$2"; shift 2 ;;
            --api-key)       API_KEY="$2"; shift 2 ;;
            --install-dir)   INSTALL_DIR="$2"; shift 2 ;;
            --port)          PORT="$2"; shift 2 ;;
            --silent)        SILENT=true; shift ;;
            -h|--help)
                echo "用法: $0 [--platform-url URL] [--customer-id ID] [--api-key KEY] [--install-dir DIR] [--port PORT] [--silent]"
                exit 0
                ;;
            *) err "未知参数: $1"; exit 1 ;;
        esac
    done
}

# ── 主流程 ────────────────────────────────────────────────────────

main() {
    echo ""
    echo "OPC200 Agent Installer v${AGENT_VERSION} (Mac/Linux)"
    echo ""

    step_check_env
    step_get_config
    step_download
    step_install
    step_register_service
    step_start_verify
    step_summary
}

parse_args "$@"
main
