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
OPENCLAW_DEFAULT_INSTALL_URL="https://openclaw.ai/install.sh"
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
LOCAL_BINARY=""
USE_PYTHON=true
REPO_ROOT=""
SCRIPT_DIR=""
FULL_RUNTIME_DEPS=false
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

    if ! $USE_PYTHON || [[ -n "$LOCAL_BINARY" ]]; then
        AGENT_BINARY="opc-agent-${OS_TYPE}-${ARCH}"
    fi

    if $USE_PYTHON && [[ -z "$LOCAL_BINARY" ]]; then
        [[ -f "$REPO_ROOT/agent/src/opc_agent/cli.py" ]] || fail $E001 "E001: 非 OPC200 仓库根目录: $REPO_ROOT（请使用 --repo-root 或在克隆仓库内执行本脚本）"
        local pyexe=python3
        command -v "$pyexe" &>/dev/null || pyexe=python
        command -v "$pyexe" &>/dev/null || fail $E001 "E001: 未找到 python3/python"
        local pmaj pmin
        pmaj="$("$pyexe" -c 'import sys; print(sys.version_info[0])')"
        pmin="$("$pyexe" -c 'import sys; print(sys.version_info[1])')"
        if [[ "$pmaj" -lt 3 ]] || { [[ "$pmaj" -eq 3 ]] && [[ "$pmin" -lt 10 ]]; }; then
            fail $E001 "E001: 需要 Python 3.10+（当前 $("$pyexe" -V 2>&1)）"
        fi
        ok "Python: $("$pyexe" -V 2>&1)；源码: $REPO_ROOT"
    fi

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
    info "2/8 获取配置"

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

# ── Step 3: 官方渠道安装 OpenClaw latest ─────────────────────────

step_install_openclaw_official() {
    info "3/8 官方渠道安装 OpenClaw latest"

    # 允许环境变量覆写安装入口，但仅允许官方域名，避免被导向私有或恶意源。
    local install_url="${OPENCLAW_INSTALL_URL:-$OPENCLAW_DEFAULT_INSTALL_URL}"
    local channel="${OPENCLAW_CHANNEL:-latest}"
    local host
    host="$(printf '%s' "$install_url" | sed -E 's#^https?://([^/]+).*$#\1#' | tr '[:upper:]' '[:lower:]')"

    [[ "$install_url" == https://* ]] || fail $E002 "E002: OPENCLAW_INSTALL_URL 必须使用 https: $install_url"
    case "$host" in
        openclaw.ai|www.openclaw.ai) ;;
        *) fail $E002 "E002: OPENCLAW_INSTALL_URL 非官方域名: $host" ;;
    esac
    if [[ "$channel" != "latest" ]]; then
        warn "OPENCLAW_CHANNEL=$channel；当前策略要求 latest，继续按 latest 执行"
        channel="latest"
    fi

    ok "OpenClaw 安装源: $install_url"
    ok "OpenClaw 渠道: $channel"
    curl -fsSL "$install_url" | bash || fail $E002 "E002: OpenClaw 官方安装失败"
    ok "OpenClaw 官方安装完成"
}

# ── Step 4: 下载 Agent ───────────────────────────────────────────

step_download() {
    if [[ -n "$LOCAL_BINARY" ]]; then
        info "4/8 使用本地二进制"
        [[ -f "$LOCAL_BINARY" ]] || fail $E001 "E001: 本地二进制不存在: $LOCAL_BINARY"
        TMP_BINARY="$LOCAL_BINARY"
        ok "使用本地二进制: $LOCAL_BINARY"
        return
    fi

    if $USE_PYTHON; then
        local reqfile="requirements-agent-runtime.txt"
        if $FULL_RUNTIME_DEPS; then
            reqfile="requirements-agent-runtime-full.txt"
            info "4/8 Python 运行环境 (venv + pip，完整依赖，体积大、耗时长)"
        else
            info "4/8 Python 运行环境 (venv + pip，精简依赖)"
        fi
        [[ -f "$REPO_ROOT/agent/scripts/$reqfile" ]] || fail $E001 "E001: 缺少 $reqfile（$REPO_ROOT）"
        local pyexe=python3
        command -v "$pyexe" &>/dev/null || pyexe=python
        mkdir -p "$INSTALL_DIR"
        local venv="$INSTALL_DIR/venv"
        "$pyexe" -m venv "$venv" || fail $E001 "E001: 无法创建 venv"
        "$venv/bin/pip" install -q -U pip || fail $E002 "E002: pip 升级失败"
        "$venv/bin/pip" install -q -r "$REPO_ROOT/agent/scripts/$reqfile" || {
            rm -rf "$INSTALL_DIR"
            fail $E002 "E002: pip 安装依赖失败"
        }
        ok "已安装运行时依赖 → $venv"
        TMP_BINARY=""
        return
    fi

    info "4/8 下载 Agent"

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

# ── Step 5: 安装部署 ─────────────────────────────────────────────

step_install() {
    info "5/8 安装部署"

    local root="$INSTALL_DIR"
    local dirs=("$root" "$root/bin" "$root/config" "$root/data" "$root/data/journal" "$root/data/exporter" "$root/logs")

    for d in "${dirs[@]}"; do
        mkdir -p "$d"
    done
    register_rollback "rm -rf '$root'"
    ok "目录结构已创建"

    if [[ -n "$LOCAL_BINARY" ]] || ! $USE_PYTHON; then
        cp "$TMP_BINARY" "$root/bin/opc-agent"
        chmod +x "$root/bin/opc-agent"
        ok "Agent 二进制已部署"
    else
        printf 'PYTHONPATH=%s\n' "$REPO_ROOT" >"$root/runtime.env"
        chmod 644 "$root/runtime.env"
        cat >"$root/bin/opc-agent" << 'EOS'
#!/usr/bin/env sh
set -eu
_ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1090
. "$_ROOT/runtime.env"
export PYTHONPATH
exec "$_ROOT/venv/bin/python" -m agent.src.opc_agent.cli "$@"
EOS
        chmod +x "$root/bin/opc-agent"
        ok "已部署 Python 启动脚本（PYTHONPATH=$REPO_ROOT）"
    fi

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

journal:
  storage_path: "${root}/data/journal"
  max_size: "1GB"

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

# ── Step 6: 注册系统服务 ─────────────────────────────────────────

step_register_service() {
    info "6/8 注册系统服务"

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
ExecStart=${agent_bin} --config ${config_yml} run
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

# ── Step 7: 启动验证 ─────────────────────────────────────────────

step_start_verify() {
    info "7/8 启动验证"

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

# ── Step 8: 完成输出 ─────────────────────────────────────────────

step_summary() {
    info "8/8 安装完成"

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
            --local-binary)  LOCAL_BINARY="$2"; USE_PYTHON=false; shift 2 ;;
            --repo-root)     REPO_ROOT="$2"; shift 2 ;;
            --binary)        USE_PYTHON=false; shift ;;
            --full-runtime-deps) FULL_RUNTIME_DEPS=true; shift ;;
            --silent)        SILENT=true; shift ;;
            -h|--help)
                echo "用法: $0 [--platform-url URL] [--customer-id ID] [--api-key KEY] [--install-dir DIR] [--port PORT]"
                echo "         [--repo-root DIR] [--binary] [--local-binary PATH] [--full-runtime-deps] [--silent]"
                echo "默认: Python venv + 仓库源码；第三步仅装精简 pip 依赖（/health + 指标推送）。"
                echo "      --full-runtime-deps 安装完整依赖（含 PyTorch 等，很慢）。"
                echo "      --binary / --local-binary 使用单文件二进制。"
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

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    [[ -z "$REPO_ROOT" ]] && REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

    step_check_env
    step_get_config
    step_install_openclaw_official
    step_download
    step_install
    step_register_service
    step_start_verify
    step_summary
}

parse_args "$@"
main
