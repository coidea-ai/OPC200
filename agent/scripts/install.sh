#!/usr/bin/env bash
# AGENT-003: OPC200 Agent Mac/Linux 安装脚本 (v2)
# 按 AGENT-001 (docs/INSTALL_SCRIPT_SPEC.md) 规范实现
# 流程: 环境检查 → 安装目录 → OpenClaw（官方/onboard/轻预装/网关）→ OPC200 Agent（venv/服务）→ 验证
# 与 install.ps1 分段与语义对齐（Mac/Linux）

set -euo pipefail

# ── 常量 ──────────────────────────────────────────────────────────

AGENT_VERSION="2.5.3"
DOWNLOAD_BASE="https://github.com/coidea-ai/OPC200/releases/download/v${AGENT_VERSION}"
SERVICE_NAME="opc200-agent"
DEFAULT_URL="http://opc200.meerkatai.cn:9091"
OPENCLAW_DEFAULT_INSTALL_URL="https://openclaw.ai/install.sh"
OPENCLAW_MIN_NODE_MAJOR=22
OPENCLAW_DEFAULT_NPM_REGISTRY="https://repo.huaweicloud.com/repository/npm/"
OPENCLAW_INSTALL_TIMEOUT_SEC=900
OPENCLAW_NET_CHECK_HOSTS=("openclaw.ai" "repo.huaweicloud.com" "github.com")
OPENCLAW_DEFAULT_PROFILE_DIR="$HOME/.openclaw"
OPENCLAW_DEFAULT_SKILLS="skill-vetter"
OPENCLAW_DEFAULT_SKILL_INSTALL_CMD="openclaw skills install"
OPENCLAW_DEFAULT_GATEWAY_PORT=18789
OPENCLAW_ONBOARD_TIMEOUT_SEC=600
OPENCLAW_GW_INSTALL_MAX_RETRY=3
OPENCLAW_GATEWAY_WARMUP_MAX_TRIES=25
OPENCLAW_GATEWAY_WARMUP_SLEEP_SEC=2
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
TENANT_ID=""
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
OPENCLAW_ONBOARD_CLI=false
OPENCLAW_SKIP_ONBOARD_CLI=false
FRESH_OPENCLAW_CLI=false

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

# WSL/终端粘贴时 read -s 无回显；提示说明 + 回车后仅报告长度，不泄露密钥
read_secret_line() {
    local __dst="$1"
    local __prompt="$2"
    local __v=""
    printf '%s' "$__prompt" >&2
    printf '\033[90m（不回显；粘贴后按回车）\033[0m\n' >&2
    IFS= read -rs __v || true
    printf '\n' >&2
    if [[ -n "$__v" ]]; then
        ok "已录入 ${#__v} 个字符（内容已隐藏）"
    fi
    printf -v "$__dst" %s "$__v"
}

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
    info "1/15 环境检查"

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

# ── Step 2: 安装目录（与 install.ps1 Initialize-InstallPaths 对齐）──

step_initialize_paths() {
    info "2/15 安装目录"
    [[ -z "$INSTALL_DIR" ]] && INSTALL_DIR="$HOME/.opc200"
    ok "InstallRoot: $INSTALL_DIR"
}

# ── Step 10: 平台与租户（第三部分；与 Get-OpcAgentPlatformConfig 对齐）──

step_opc200_platform_config() {
    info "10/15 平台与租户 (OPC200 Agent)"

    if $SILENT; then
        if [[ -n "${OPC200_PLATFORM_URL:-}" ]]; then
            PLATFORM_URL="$OPC200_PLATFORM_URL"
        fi
        if [[ -z "$PLATFORM_URL" ]]; then
            PLATFORM_URL="$DEFAULT_URL"
        fi
        local tid="${TENANT_ID:-}"
        [[ -z "$tid" && -n "${OPC200_TENANT_ID:-}" ]] && tid="$OPC200_TENANT_ID"
        [[ -z "$tid" ]] && fail $E001 "E001: 静默须 --opc200-tenant-id 或环境变量 OPC200_TENANT_ID"
        TENANT_ID="$tid"
        if [[ -z "${API_KEY:-}" ]]; then
            if [[ -n "${OPC200_API_KEY:-}" ]]; then
                API_KEY="$OPC200_API_KEY"
            elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
                API_KEY="$ANTHROPIC_API_KEY"
            elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
                API_KEY="$OPENAI_API_KEY"
            elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
                API_KEY="$GEMINI_API_KEY"
            elif [[ -n "${CUSTOM_API_KEY:-}" ]]; then
                API_KEY="$CUSTOM_API_KEY"
            else
                fail $E001 "E001: 静默须 OPC200 平台 ApiKey：OPC200_API_KEY，或 OpenClaw 模型密钥环境变量"
            fi
        fi
    else
        local input
        read -rp "平台地址 [${DEFAULT_URL}]: " input
        PLATFORM_URL="${input:-$DEFAULT_URL}"
        while [[ -z "${TENANT_ID:-}" ]]; do
            read -rp "租户 ID (Tenant ID，必需): " TENANT_ID
            [[ -z "$TENANT_ID" ]] && err "不能为空"
        done
        if [[ -z "${API_KEY:-}" ]]; then
            [[ -n "${ANTHROPIC_API_KEY:-}" ]] && API_KEY="$ANTHROPIC_API_KEY"
            [[ -z "${API_KEY:-}" && -n "${OPENAI_API_KEY:-}" ]] && API_KEY="$OPENAI_API_KEY"
            [[ -z "${API_KEY:-}" && -n "${GEMINI_API_KEY:-}" ]] && API_KEY="$GEMINI_API_KEY"
            [[ -z "${API_KEY:-}" && -n "${CUSTOM_API_KEY:-}" ]] && API_KEY="$CUSTOM_API_KEY"
        fi
        if [[ -z "${API_KEY:-}" ]]; then
            read_secret_line API_KEY "平台 API Key (OpenClaw 未采集密钥时必填): "
            [[ -z "$API_KEY" ]] && fail $E001 "E001: 平台 API Key 不能为空"
        else
            ok "已复用 OpenClaw 阶段的密钥作为平台 ApiKey"
        fi
    fi
    ok "平台: $PLATFORM_URL | Tenant: $TENANT_ID"
}

# ── Step 3: 准备 Node.js（Linux）──────────────────────────────────

# sudo 时 PATH 常不含 /usr/local/bin 或 nvm，导致误判「未安装」；可 export NODE_BINARY=/path/to/node 强制指定
_get_node_executable() {
    if [[ -n "${NODE_BINARY:-}" && -x "${NODE_BINARY}" ]]; then
        printf '%s\n' "$NODE_BINARY"
        return 0
    fi
    if command -v node &>/dev/null; then
        command -v node
        return 0
    fi
    local p glob home
    for p in /usr/local/bin/node /usr/bin/node /opt/nodejs/bin/node; do
        if [[ -x "$p" ]]; then
            printf '%s\n' "$p"
            return 0
        fi
    done
    if [[ -n "${SUDO_USER:-}" ]]; then
        home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)" || true
        if [[ -n "$home" ]]; then
            glob="$(ls -1 "$home"/.nvm/versions/node/*/bin/node 2>/dev/null | sort -V | tail -n1)"
            if [[ -n "$glob" && -x "$glob" ]]; then
                printf '%s\n' "$glob"
                return 0
            fi
        fi
    fi
    glob="$(ls -1 "${HOME}"/.nvm/versions/node/*/bin/node 2>/dev/null | sort -V | tail -n1)"
    if [[ -n "$glob" && -x "$glob" ]]; then
        printf '%s\n' "$glob"
        return 0
    fi
    return 1
}

get_node_major_version() {
    local node_exe ver
    node_exe="$(_get_node_executable 2>/dev/null || true)"
    if [[ -z "$node_exe" ]]; then
        echo "0"
        return
    fi
    ver="$("$node_exe" -v 2>/dev/null || true)"
    if [[ "$ver" =~ ^v([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
        return
    fi
    echo "0"
}

install_node_linux_from_official() {
    local node_arch
    case "$(uname -m)" in
        x86_64|amd64) node_arch="x64" ;;
        aarch64|arm64) node_arch="arm64" ;;
        *) fail $E002 "E002: Node 官方包不支持当前架构: $(uname -m)" ;;
    esac

    # 使用 index.json 选取最新 v22.x（含 linux-${arch} 制品），避免目录页 HTML / 镜像格式差异导致 sed 匹配失败
    local json tarball ver_tag url tmpdir extracted
    json="$(curl -fsSL "https://nodejs.org/dist/index.json" 2>/dev/null)" || fail $E002 "E002: 无法访问 nodejs.org（下载 Node 22）"
    tarball="$(printf '%s\n' "$json" | python3 -c '
import json, re, sys
arch = sys.argv[1]
linux_key = "linux-" + arch
j = json.load(sys.stdin)
for row in j:
    v = row.get("version") or ""
    if not re.match(r"^v22\.", v):
        continue
    if linux_key not in (row.get("files") or []):
        continue
    print("node-{}-linux-{}.tar.xz".format(v, arch))
    sys.exit(0)
sys.exit(1)
' "$node_arch")" || true
    [[ -n "$tarball" ]] || fail $E002 "E002: 未找到 Node 22 Linux 安装包（架构 ${node_arch}）"
    ver_tag="${tarball#node-}"
    ver_tag="${ver_tag%-linux-*}"
    url="https://nodejs.org/dist/${ver_tag}/${tarball}"

    tmpdir="$(mktemp -d)"
    register_rollback "rm -rf '${tmpdir}'"
    ok "下载 Node.js: $url"
    curl -fsSL "$url" -o "${tmpdir}/node.tar.xz" || fail $E002 "E002: 下载 Node 22 失败"
    tar -xJf "${tmpdir}/node.tar.xz" -C "$tmpdir" || fail $E002 "E002: 解压 Node 22 失败"
    extracted="$(ls -d "${tmpdir}"/node-v22* 2>/dev/null | head -n1)"
    [[ -n "$extracted" ]] || fail $E002 "E002: Node 22 解压目录异常"

    cp -f "${extracted}/bin/node" /usr/local/bin/node || fail $E002 "E002: 安装 node 失败"
    cp -f "${extracted}/bin/npm" /usr/local/bin/npm || true
    cp -f "${extracted}/bin/npx" /usr/local/bin/npx || true
    rm -rf /usr/local/lib/node_modules
    mkdir -p /usr/local/lib/node_modules
    cp -a "${extracted}/lib/node_modules/." /usr/local/lib/node_modules/ || fail $E002 "E002: 安装 node_modules 失败"
    ok "Node.js 22 已安装到 /usr/local/bin"
}

step_prepare_node_runtime() {
    info "3/15 准备 Node.js（OpenClaw 需要 v${OPENCLAW_MIN_NODE_MAJOR}+）"

    if [[ "$OS_TYPE" != "linux" ]]; then
        ok "当前非 Linux，跳过 Node.js 预安装步骤"
        return
    fi

    # sudo 默认 secure_path 可能缺少 /usr/local/bin（用户手动安装的 node 常在此）
    export PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
    if [[ -z "${NODE_BINARY:-}" ]]; then
        local _nx
        _nx="$(_get_node_executable 2>/dev/null || true)"
        [[ -n "$_nx" ]] && export NODE_BINARY="$_nx"
    fi
    if [[ -n "${NODE_BINARY:-}" ]]; then
        export PATH="$(dirname "$NODE_BINARY"):${PATH:-}"
    fi

    local major
    major="$(get_node_major_version)"
    if [[ "$major" -ge "$OPENCLAW_MIN_NODE_MAJOR" ]]; then
        ok "Node.js 主版本 ${major} 已满足要求"
        return
    fi

    if [[ "$major" -gt 0 ]]; then
        warn "当前 Node.js 主版本 ${major}，需要 ${OPENCLAW_MIN_NODE_MAJOR}+，将自动安装 Node 22"
    else
        warn "未检测到 Node.js，将自动安装 Node 22"
    fi

    install_node_linux_from_official
    hash -r
    major="$(get_node_major_version)"
    [[ "$major" -ge "$OPENCLAW_MIN_NODE_MAJOR" ]] || fail $E002 "E002: Node.js 版本仍低于 ${OPENCLAW_MIN_NODE_MAJOR}+"
    ok "Node.js 主版本 ${major} 已就绪"
}

# ── 网络预检 ─────────────────────────────────────────────────────

step_network_check() {
    info "4/15 网络连通性预检"
    local all_ok=true
    for h in "${OPENCLAW_NET_CHECK_HOSTS[@]}"; do
        if command -v nc &>/dev/null; then
            nc -z -w 5 "$h" 443 &>/dev/null && ok "可达: $h" || { warn "不可达: $h（安装可能变慢或失败）"; all_ok=false; }
        elif command -v curl &>/dev/null; then
            curl -sf --connect-timeout 5 "https://$h" -o /dev/null &>/dev/null && ok "可达: $h" || { warn "不可达: $h（安装可能变慢或失败）"; all_ok=false; }
        else
            warn "无 nc/curl，跳过 $h 连通性检测"
        fi
    done
    if ! $all_ok; then
        warn "部分主机不可达；若安装超时，请检查网络或稍后重试"
    fi
}

# sudo 下 HOME 常为 /root，openclaw 可能装在原用户的 ~/.local/bin 或 npm global prefix，需补全 PATH
_expand_path_for_openclaw_cli() {
    export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
    local pfx nd su_home
    pfx="$(npm config get prefix 2>/dev/null)" || true
    if [[ -n "$pfx" && -d "$pfx/bin" ]]; then
        export PATH="$pfx/bin:${PATH:-}"
    fi
    if [[ -n "${NODE_BINARY:-}" && -x "${NODE_BINARY}" ]]; then
        nd="$(dirname "$NODE_BINARY")"
        export PATH="$nd:${PATH:-}"
    fi
    if command -v node &>/dev/null; then
        nd="$(dirname "$(command -v node)")"
        export PATH="$nd:${PATH:-}"
    fi
    if [[ -n "${SUDO_USER:-}" ]]; then
        su_home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)" || true
        if [[ -n "$su_home" ]]; then
            [[ -d "$su_home/.local/bin" ]] && export PATH="$su_home/.local/bin:${PATH:-}"
            if [[ -d "$su_home/.nvm/versions/node" ]]; then
                nd="$(ls -1 "$su_home"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -n1)"
                [[ -n "$nd" && -d "$nd" ]] && export PATH="$nd:${PATH:-}"
            fi
        fi
    fi
    hash -r 2>/dev/null || true
}

# WSL 未启用 systemd 时 user 服务不可用；onboard 与 gateway install 均依赖 systemctl（见 _assert_linux_systemd_ready_for_onboard_daemon）
_is_wsl() {
    [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null
}

_opc200_msg_user_systemd_required() {
    local uname="${1:-$(id -un)}"
    printf '%s\n' "" >&2
    warn "【第 6 步已中止】OpenClaw 安装网关守护进程（--install-daemon）需要用户「${uname}」的用户级系统服务，当前环境未就绪。"
    if _is_wsl; then
        warn "请按如下操作依次执行（复制整行命令即可）："
        warn "  1. 若从没开过 WSL 的 systemd，在本 WSL 终端执行一次（已开过的可跳过）："
        warn "       printf '%s\\n' '[boot]' 'systemd=true' | sudo tee /etc/wsl.conf"
        warn "  2. 在 Windows 打开 PowerShell，执行："
        warn "       wsl --shutdown"
        warn "  3. 重新打开本 WSL，执行："
        warn "       sudo loginctl enable-linger ${uname}"
        warn "  4. 再在 Windows PowerShell 执行："
        warn "       wsl --shutdown"
        warn "  5. 再次打开本 WSL，重新运行本安装脚本。"
    else
        warn "在本机终端执行后注销或重启，再重新运行安装脚本："
        warn "       sudo loginctl enable-linger ${uname}"
    fi
    warn "若不想装用户级网关服务，可先执行：export OPENCLAW_ONBOARD_SKIP_DAEMON=1"
    printf '%s\n' "" >&2
}

_opc200_abort_user_systemd_setup() {
    local uname="${1:-$(id -un)}"
    _opc200_msg_user_systemd_required "$uname"
    warn "安装已退出（退出码 ${E001}）。"
    rollback
    exit "$E001"
}

_assert_linux_user_systemd_session_for_openclaw() {
    local uid uname bus
    if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" ]]; then
        uname="$SUDO_USER"
    else
        uname="$(id -un)"
    fi
    uid="$(id -u "$uname" 2>/dev/null)" || fail $E001 "E001: 无法解析用户 $uname"
    bus="/run/user/${uid}/bus"
    if [[ ! -S "$bus" ]]; then
        _opc200_abort_user_systemd_setup "$uname"
    fi
    if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" ]]; then
        sudo -u "$SUDO_USER" -H env \
            XDG_RUNTIME_DIR="/run/user/${uid}" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
            systemctl --user is-system-running &>/dev/null \
            || _opc200_abort_user_systemd_setup "$uname"
    else
        systemctl --user is-system-running &>/dev/null \
            || _opc200_abort_user_systemd_setup "$uname"
    fi
}

_assert_linux_systemd_ready_for_onboard_daemon() {
    if ! command -v systemctl &>/dev/null; then
        fail $E001 "E001: 未找到 systemctl，无法为 OpenClaw onboard 安装网关用户服务。请使用带 systemd 的 Linux，或显式设置 OPENCLAW_ONBOARD_SKIP_DAEMON=1（不推荐）。"
    fi
    local st=""
    st="$(systemctl is-system-running 2>/dev/null || true)"
    if ! systemctl is-system-running &>/dev/null; then
        if _is_wsl; then
            fail $E001 "E001: WSL 上 systemd 未就绪（systemctl is-system-running: ${st:-错误}）。请在 /etc/wsl.conf 添加 [boot] 段并设置 systemd=true；在 Windows PowerShell 执行 wsl --shutdown 后重新打开本发行版，再运行安装。若暂无法启用 systemd，可显式设置 OPENCLAW_ONBOARD_SKIP_DAEMON=1（不推荐）。"
        fi
        fail $E001 "E001: systemd 未就绪（systemctl is-system-running: ${st:-错误}）。请修复系统初始化后重试，或显式设置 OPENCLAW_ONBOARD_SKIP_DAEMON=1（不推荐）。"
    fi
    _assert_linux_user_systemd_session_for_openclaw
}

# sudo 安装时 OpenClaw 状态目录用「实际用户」的 ~/ ，不用 /root（除非显式 OPENCLAW_STATE_HOME 或真实 root 会话）
_openclaw_state_home() {
    if [[ -n "${OPENCLAW_STATE_HOME:-}" ]]; then
        printf '%s' "${OPENCLAW_STATE_HOME}"
        return
    fi
    if [[ -n "${SUDO_USER:-}" ]]; then
        local h
        h="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)"
        if [[ -n "$h" ]]; then
            printf '%s' "$h"
            return
        fi
    fi
    if [[ $EUID -eq 0 ]]; then
        printf '%s' "/root"
        return
    fi
    printf '%s' "${HOME:-}"
}

_openclaw_run() {
    local oh="$1"
    shift
    [[ -n "$oh" ]] || return 1
    local -a runenv=(HOME="$oh" PATH="${PATH}")
    if [[ "${OS_TYPE:-}" == "linux" ]]; then
        local u uid bus
        if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "$oh" != "/root" ]]; then
            u="$SUDO_USER"
        elif [[ $EUID -eq 0 && "$oh" == "/root" ]]; then
            u="root"
        else
            u="$(id -un 2>/dev/null || true)"
        fi
        if [[ -n "$u" ]]; then
            uid="$(id -u "$u" 2>/dev/null)" || uid=""
            if [[ -n "$uid" ]]; then
                bus="/run/user/${uid}/bus"
                if [[ -S "$bus" ]]; then
                    runenv+=(XDG_RUNTIME_DIR="/run/user/${uid}" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}")
                fi
            fi
        fi
    fi
    if [[ $EUID -eq 0 && "$oh" == "/root" ]]; then
        env "${runenv[@]}" "$@"
    elif [[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "$oh" != "/root" ]]; then
        sudo -u "$SUDO_USER" -H env "${runenv[@]}" "$@"
    else
        env "${runenv[@]}" "$@"
    fi
}

# 网关仍不监听时：先 start / user systemd，再 nohup（WSL 与「systemd 在但 user 单元未起」均适用）
step_openclaw_gateway_wsl_fallback() {
    [[ "$OS_TYPE" == "linux" ]] || return 0
    _expand_path_for_openclaw_cli
    if ! command -v openclaw &>/dev/null; then
        return 0
    fi
    local exe gw_port oc_home su_home logf pt
    exe="$(command -v openclaw)"
    oc_home="$(_openclaw_state_home)"
    [[ -n "$oc_home" ]] || {
        warn "无法确定 OpenClaw 配置家目录（HOME），跳过 8b"
        return 0
    }
    gw_port="${OPENCLAW_GATEWAY_PORT:-$OPENCLAW_DEFAULT_GATEWAY_PORT}"
    pt="$(_openclaw_run "$oc_home" openclaw config get gateway.port 2>/dev/null | tr -d '\r\n"')" || true
    [[ "$pt" =~ ^[0-9]+$ ]] && gw_port="$pt"

    if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
        ok "网关 RPC 已就绪"
        return 0
    fi
    if command -v curl &>/dev/null && curl -sf --connect-timeout 2 "http://127.0.0.1:${gw_port}/health" &>/dev/null; then
        ok "网关 HTTP /health 已就绪（${gw_port}）"
        return 0
    fi

    info "8b/15 网关未监听 ${gw_port}，尝试 gateway start / systemctl --user …（OpenClaw 状态目录: ${oc_home}/.openclaw）"
    _openclaw_run "$oc_home" openclaw gateway start 2>&1 || true
    if [[ "$oc_home" == "/root" ]] && [[ $EUID -eq 0 ]]; then
        env HOME=/root XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/0}" systemctl --user start openclaw-gateway.service 2>/dev/null || true
    elif [[ -n "${SUDO_USER:-}" ]]; then
        su_home="$oc_home"
        sudo -u "$SUDO_USER" -H env HOME="$su_home" PATH="${PATH}" XDG_RUNTIME_DIR="/run/user/$(id -u "$SUDO_USER" 2>/dev/null)" systemctl --user start openclaw-gateway.service 2>/dev/null || true
    else
        systemctl --user start openclaw-gateway.service 2>/dev/null || true
    fi
    sleep 4
    if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
        ok "网关 RPC 在补启动后就绪"
        return 0
    fi
    if command -v curl &>/dev/null && curl -sf --connect-timeout 2 "http://127.0.0.1:${gw_port}/health" &>/dev/null; then
        ok "网关 HTTP /health 在补启动后就绪（${gw_port}）"
        return 0
    fi

    su_home="$oc_home"
    logf="${su_home}/.openclaw/opc200-gateway-nohup.log"
    if _is_wsl; then
        warn "WSL：若长期依赖 systemd user，可在 /etc/wsl.conf 设 [boot] systemd=true 后 wsl --shutdown"
    fi
    warn "尝试 nohup 后台启动网关（日志: $logf）"
    mkdir -p "${su_home}/.openclaw" 2>/dev/null || true
    if [[ "$oc_home" == "/root" ]] && [[ $EUID -eq 0 ]]; then
        if pgrep -f 'openclaw gateway' >/dev/null 2>&1; then
            ok "已有 openclaw gateway 进程"
        else
            env HOME=/root PATH="${PATH}" bash -c "cd /root && nohup \"${exe}\" gateway --port \"${gw_port}\" >>\"${logf}\" 2>&1 &" || warn "后台启动网关失败"
        fi
    elif [[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "$oc_home" != "/root" ]]; then
        sudo -u "$SUDO_USER" -H bash -c "
            export HOME=\"${su_home}\"
            export PATH=\"${PATH}\"
            cd \"\$HOME\" || exit 1
            if pgrep -u \"${SUDO_USER}\" -f 'openclaw gateway' >/dev/null 2>&1; then exit 0; fi
            nohup \"${exe}\" gateway --port \"${gw_port}\" >>\"${logf}\" 2>&1 &
        " || warn "后台启动网关失败（可手动: nohup openclaw gateway --port ${gw_port} &）"
    else
        if pgrep -f 'openclaw gateway' >/dev/null 2>&1; then
            ok "已有 openclaw gateway 进程"
        else
            ( cd "$su_home" && nohup "$exe" gateway --port "$gw_port" >>"$logf" 2>&1 & ) || warn "后台启动网关失败"
        fi
    fi
    sleep 4
    local i
    for i in $(seq 1 15); do
        if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
            ok "网关 RPC 已就绪"
            return 0
        fi
        if command -v curl &>/dev/null && curl -sf --connect-timeout 2 "http://127.0.0.1:${gw_port}/health" &>/dev/null; then
            ok "网关 HTTP /health 已就绪（${gw_port}）"
            return 0
        fi
        sleep 2
    done
    warn "网关仍未监听 ${gw_port}。请查看: $logf；并执行: openclaw doctor；openclaw gateway status；openclaw gateway install --port ${gw_port} && openclaw gateway restart"
}

# ── Step 4: 官方渠道安装 OpenClaw latest ─────────────────────────

step_install_openclaw_official() {
    hash -r 2>/dev/null || true
    _expand_path_for_openclaw_cli
    if command -v openclaw &>/dev/null; then
        FRESH_OPENCLAW_CLI=false
        info "5/15 官方渠道安装 OpenClaw latest（已存在 CLI，跳过）"
        ok "已检测到 openclaw CLI"
        return 0
    fi
    FRESH_OPENCLAW_CLI=true
    info "5/15 官方渠道安装 OpenClaw latest"

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

    # npm registry：固定使用脚本内默认（npmmirror）
    local npm_registry="$OPENCLAW_DEFAULT_NPM_REGISTRY"

    ok "OpenClaw 安装源: $install_url"
    ok "OpenClaw 渠道: $channel"
    ok "npm registry: $npm_registry"

    # 实时输出 + 超时控制 + 心跳：若长时间无新日志，每 15s 提示一次运行状态
    local log_file
    log_file="$(mktemp /tmp/opc200-openclaw-install-XXXXXX.log)"
    ok "安装日志: $log_file"
    printf "\033[90m  [i] 下方 [openclaw] 为实时输出；若暂时无输出，将每 15s 提示已运行时长与日志末行。\033[0m\n"

    local exit_code=0
    local cmd_start now elapsed last_hb=0 cursor=0 line last_line=""
    local run_cmd=(
        timeout "$OPENCLAW_INSTALL_TIMEOUT_SEC"
        bash -c "curl -fsSL '$install_url' | bash"
    )
    (
        NPM_CONFIG_REGISTRY="$npm_registry" \
        NPM_CONFIG_FETCH_RETRIES="3" \
        NPM_CONFIG_FETCH_RETRY_MINTIMEOUT="10000" \
        NPM_CONFIG_FETCH_TIMEOUT="60000" \
        NODE_LLAMA_CPP_SKIP_DOWNLOAD="1" \
        OPENCLAW_NO_ONBOARD="1" \
            "${run_cmd[@]}"
    ) >"$log_file" 2>&1 &
    local install_pid=$!
    cmd_start="$(date +%s)"

    while kill -0 "$install_pid" 2>/dev/null; do
        if [[ -f "$log_file" ]]; then
            while IFS= read -r line; do
                [[ -z "$line" ]] && continue
                printf '  [openclaw] %s\n' "$line"
                last_line="$line"
            done < <(tail -n +"$((cursor + 1))" "$log_file" 2>/dev/null || true)
            cursor="$(wc -l <"$log_file" 2>/dev/null || echo "$cursor")"
        fi

        now="$(date +%s)"
        elapsed=$((now - cmd_start))
        if (( now - last_hb >= 15 )); then
            if [[ -n "$last_line" ]]; then
                printf "\033[90m  [openclaw] 仍在安装（已运行 %ss），最新输出：%s\033[0m\n" "$elapsed" "$last_line"
            else
                printf "\033[90m  [openclaw] 仍在安装（已运行 %ss），末行尚空（npm 可能仍在缓冲）\033[0m\n" "$elapsed"
            fi
            last_hb="$now"
        fi
        sleep 0.5
    done

    wait "$install_pid" || exit_code=$?
    if [[ -f "$log_file" ]]; then
        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            printf '  [openclaw] %s\n' "$line"
        done < <(tail -n +"$((cursor + 1))" "$log_file" 2>/dev/null || true)
    fi

    if [[ "$exit_code" -eq 124 ]]; then
        fail $E002 "E002: OpenClaw 官方安装超时（>${OPENCLAW_INSTALL_TIMEOUT_SEC}s）。日志: $log_file"
    elif [[ "$exit_code" -ne 0 ]]; then
        fail $E002 "E002: OpenClaw 官方安装失败（退出码 ${exit_code}）。日志: $log_file"
    fi

    ok "OpenClaw 官方安装完成"
    _expand_path_for_openclaw_cli
    if ! command -v openclaw &>/dev/null; then
        warn "官方安装已完成，但当前 PATH 仍找不到 openclaw；后续步骤将再尝试补全 PATH。若仍失败请执行: $(command -v npm 2>/dev/null || echo npm) config get prefix，并把该目录下的 bin 加入 PATH"
    fi
}

# ── Step 5: 轻预装层（skills + 文档）────────────────────────────

step_preinstall_openclaw_assets() {
    info "7/15 轻预装层（tools + skills + 文档）"
    _expand_path_for_openclaw_cli

    local profile_dir
    if [[ -n "${OPENCLAW_PROFILE_DIR:-}" ]]; then
        profile_dir="$OPENCLAW_PROFILE_DIR"
    else
        profile_dir="$(_openclaw_state_home)/.openclaw"
    fi
    local skills_csv="${OPENCLAW_PREINSTALL_SKILLS:-$OPENCLAW_DEFAULT_SKILLS}"
    local skill_install_cmd="${OPENCLAW_SKILL_INSTALL_CMD:-$OPENCLAW_DEFAULT_SKILL_INSTALL_CMD}"
    local failed=0
    local templates_dir="$SCRIPT_DIR/openclaw-templates"

    mkdir -p "$profile_dir"
    ok "OpenClaw 配置目录: $profile_dir"

    if command -v openclaw &>/dev/null; then
        local oc_home_pre
        oc_home_pre="$(_openclaw_state_home)"
        [[ -n "$oc_home_pre" ]] || oc_home_pre="${HOME:-}"
        ok "openclaw config set tools.profile full"
        if _openclaw_run "$oc_home_pre" openclaw config set tools.profile full; then
            ok "tools.profile=full"
        else
            warn "tools.profile 未写入；可稍后手动: openclaw config set tools.profile full"
        fi
    else
        warn "未找到 openclaw，跳过 tools.profile"
    fi

    # skills 安装失败按策略仅告警，不中断安装流程。
    if [[ -n "$skills_csv" ]]; then
        IFS=',' read -r -a skills <<< "$skills_csv"
        for skill in "${skills[@]}"; do
            skill="$(printf '%s' "$skill" | xargs)"
            [[ -z "$skill" ]] && continue
            oc_home_pre="$(_openclaw_state_home)"
            [[ -n "$oc_home_pre" ]] || oc_home_pre="${HOME:-}"
            local sk_ok=1
            if [[ "$skill_install_cmd" == "$OPENCLAW_DEFAULT_SKILL_INSTALL_CMD" ]]; then
                _openclaw_run "$oc_home_pre" openclaw skills install "$skill" && sk_ok=0
            else
                _openclaw_run "$oc_home_pre" bash -lc "$(printf '%q ' $skill_install_cmd)$(printf '%q' "$skill")" && sk_ok=0
            fi
            if [[ "$sk_ok" -eq 0 ]]; then
                ok "skills 已安装: $skill"
            else
                warn "skills 安装失败（已忽略）: $skill"
                failed=1
            fi
        done
    else
        warn "未配置 OPENCLAW_PREINSTALL_SKILLS，跳过 skills 安装"
    fi

    # 模板文件采用“存在则写 .new”的策略，避免覆盖用户自定义内容。
    _write_doc_template_from_file "$templates_dir/SOUL.md" "$profile_dir/SOUL.md"
    _write_doc_template_from_file "$templates_dir/IDENTITY.md" "$profile_dir/IDENTITY.md"
    _write_doc_template_from_file "$templates_dir/AGENTS.md" "$profile_dir/AGENTS.md"

    if [[ "$failed" -eq 1 ]]; then
        warn "部分 skills 安装失败，已按策略继续安装"
    fi
}

step_openclaw_onboard() {
    if $OPENCLAW_SKIP_ONBOARD_CLI || [[ "${OPENCLAW_SKIP_ONBOARD:-}" == "1" ]]; then
        return 0
    fi
    if [[ "${OPENCLAW_ONBOARD:-}" == "0" ]]; then
        return 0
    fi
    if $SILENT; then
        if ! $OPENCLAW_ONBOARD_CLI && [[ "${OPENCLAW_ONBOARD:-}" != "1" ]]; then
            return 0
        fi
    fi

    info "6/15 OpenClaw 首次配置（官方 onboard --non-interactive）"
    _expand_path_for_openclaw_cli
    if ! $SILENT; then
        printf "\033[90m  OpenClaw CLI 已就绪。下面采集模型/网关所需最少信息；随后自动执行官方非交互 onboard。\033[0m\n"
    fi

    if ! command -v openclaw &>/dev/null; then
        warn "未找到 openclaw（PATH 未刷新或安装未完成），跳过 onboard。请新开 shell 后执行: openclaw onboard --non-interactive ..."
        return 0
    fi

    local gw_port="${OPENCLAW_GATEWAY_PORT:-$OPENCLAW_DEFAULT_GATEWAY_PORT}"
    local auth="${OPENCLAW_AUTH_CHOICE:-}"
    auth="$(printf '%s' "$auth" | xargs)"

    if $SILENT; then
        [[ -n "$auth" ]] || fail $E001 "E001: 静默安装且启用 OpenClaw onboard 时必须设置 OPENCLAW_AUTH_CHOICE"
    elif [[ -z "$auth" ]]; then
        echo ""
        echo "OpenClaw 模型认证（输入序号）:"
        echo "  1) Anthropic API Key (apiKey)"
        echo "  2) OpenAI API Key (openai-api-key)"
        echo "  3) Google Gemini API Key (gemini-api-key)"
        echo "  4) OpenAI 兼容自定义端点 (custom-api-key)"
        local pick=""
        read -rp "选择 [1-4]: " pick || true
        case "$(printf '%s' "$pick" | xargs)" in
            1) auth="apiKey" ;;
            2) auth="openai-api-key" ;;
            3) auth="gemini-api-key" ;;
            4) auth="custom-api-key" ;;
            *) fail $E001 "E001: 无效选择（请输入 1-4）" ;;
        esac
    fi

    [[ "$auth" != "skip" ]] || fail $E001 "E001: 已不再支持 skip（跳过密钥）；请使用 apiKey、openai-api-key、gemini-api-key 或 custom-api-key，并配置对应密钥"

    local secret_mode="${OPENCLAW_SECRET_INPUT_MODE:-plaintext}"
    secret_mode="$(printf '%s' "$secret_mode" | xargs)"
    [[ "$secret_mode" == "plaintext" || "$secret_mode" == "ref" ]] || fail $E001 "E001: OPENCLAW_SECRET_INPUT_MODE 仅支持 plaintext 或 ref"

    local v_anth="" v_openai="" v_gemini="" v_custom_key="" v_custom_url="" v_custom_model=""
    if ! $SILENT; then
        local line=""
        case "$auth" in
            apiKey)
                read_secret_line line "Anthropic API Key: "
                [[ -n "$line" ]] || fail $E001 "E001: API Key 不能为空"
                v_anth="$line"
                ;;
            openai-api-key)
                read_secret_line line "OpenAI API Key: "
                [[ -n "$line" ]] || fail $E001 "E001: API Key 不能为空"
                v_openai="$line"
                ;;
            gemini-api-key)
                read_secret_line line "Gemini API Key: "
                [[ -n "$line" ]] || fail $E001 "E001: API Key 不能为空"
                v_gemini="$line"
                ;;
            custom-api-key)
                local bu="" mid=""
                read -rp "自定义 Base URL (OPENAI 兼容 v1): " bu || true
                read -rp "模型 ID (custom-model-id): " mid || true
                [[ -n "$bu" && -n "$mid" ]] || fail $E001 "E001: custom 需要 base_url 与 model_id"
                read_secret_line line "API Key (CUSTOM_API_KEY): "
                [[ -n "$line" ]] || fail $E001 "E001: API Key 不能为空"
                v_custom_url="$bu"
                v_custom_model="$mid"
                v_custom_key="$line"
                ;;
        esac
    fi

    case "$auth" in
        apiKey)
            if [[ "$secret_mode" == "ref" ]]; then
                [[ -n "${ANTHROPIC_API_KEY:-}" ]] || fail $E001 "E001: ref 模式需在环境中设置 ANTHROPIC_API_KEY"
            else
                if $SILENT; then
                    [[ -n "${ANTHROPIC_API_KEY:-}" ]] || fail $E001 "E001: 需提供 ANTHROPIC_API_KEY（静默）"
                else
                    [[ -n "$v_anth" ]] || fail $E001 "E001: 需提供 ANTHROPIC_API_KEY（交互）"
                fi
            fi
            ;;
        openai-api-key)
            if $SILENT; then
                [[ -n "${OPENAI_API_KEY:-}" ]] || fail $E001 "E001: 需提供 OPENAI_API_KEY"
            else
                [[ -n "$v_openai" ]] || fail $E001 "E001: 需提供 OPENAI_API_KEY"
            fi
            ;;
        gemini-api-key)
            if $SILENT; then
                [[ -n "${GEMINI_API_KEY:-}" ]] || fail $E001 "E001: 需提供 GEMINI_API_KEY"
            else
                [[ -n "$v_gemini" ]] || fail $E001 "E001: 需提供 GEMINI_API_KEY"
            fi
            ;;
        custom-api-key)
            if $SILENT; then
                [[ -n "${OPENCLAW_CUSTOM_BASE_URL:-}" && -n "${OPENCLAW_CUSTOM_MODEL_ID:-}" ]] || fail $E001 "E001: custom-api-key 需 OPENCLAW_CUSTOM_BASE_URL 与 OPENCLAW_CUSTOM_MODEL_ID"
                if [[ "$secret_mode" == "plaintext" ]]; then
                    [[ -n "${CUSTOM_API_KEY:-}" ]] || fail $E001 "E001: custom-api-key plaintext 需 CUSTOM_API_KEY"
                fi
            else
                [[ -n "$v_custom_url" && -n "$v_custom_model" ]] || fail $E001 "E001: custom-api-key 需 base_url 与 model_id"
                if [[ "$secret_mode" == "plaintext" ]]; then
                    [[ -n "$v_custom_key" ]] || fail $E001 "E001: custom-api-key plaintext 需 API Key"
                fi
            fi
            ;;
        *) fail $E001 "E001: 不支持的 OPENCLAW_AUTH_CHOICE: $auth（支持 apiKey|openai-api-key|gemini-api-key|custom-api-key）" ;;
    esac

    # 官方非交互 onboard 要求显式风险确认，见 https://docs.openclaw.ai/security
    # Linux 默认 --install-daemon：须先有可用 systemd（WSL 需在 wsl.conf 启用）；否则 fail 或显式 OPENCLAW_ONBOARD_SKIP_DAEMON=1
    local use_onboard_daemon=true
    if [[ "${OPENCLAW_ONBOARD_SKIP_DAEMON:-}" == "1" ]]; then
        use_onboard_daemon=false
    elif [[ "${OPENCLAW_ONBOARD_FORCE_DAEMON:-}" == "1" ]]; then
        [[ "$OS_TYPE" == "linux" ]] && _assert_linux_systemd_ready_for_onboard_daemon
    elif [[ "$OS_TYPE" == "linux" ]]; then
        _assert_linux_systemd_ready_for_onboard_daemon
    fi

    local -a oc_args=(
        onboard --non-interactive --accept-risk --mode local
        --auth-choice "$auth"
        --secret-input-mode "$secret_mode"
        --gateway-port "$gw_port"
        --gateway-bind loopback
        --skip-skills
    )
    if $use_onboard_daemon; then
        oc_args+=(--install-daemon --daemon-runtime node)
    else
        warn "onboard 使用 --skip-health（已设 OPENCLAW_ONBOARD_SKIP_DAEMON=1，未安装网关守护进程）；网关由后续步骤处理。"
        oc_args+=(--skip-health)
    fi
    if [[ "$auth" == "custom-api-key" ]]; then
        if $SILENT; then
            oc_args+=(--custom-base-url "$OPENCLAW_CUSTOM_BASE_URL" --custom-model-id "$OPENCLAW_CUSTOM_MODEL_ID")
        else
            oc_args+=(--custom-base-url "$v_custom_url" --custom-model-id "$v_custom_model")
        fi
        oc_args+=(--custom-compatibility "${OPENCLAW_CUSTOM_COMPATIBILITY:-openai}")
        [[ -n "${OPENCLAW_CUSTOM_PROVIDER_ID:-}" ]] && oc_args+=(--custom-provider-id "$OPENCLAW_CUSTOM_PROVIDER_ID")
    fi
    ok "执行 openclaw onboard --non-interactive（auth=$auth gatewayPort=$gw_port secret=$secret_mode installDaemon=$use_onboard_daemon）"

    local ob_deadline="${OPENCLAW_ONBOARD_TIMEOUT_SEC:-600}"
    local ob_log exit_code=0 oc_home_ob
    oc_home_ob="$(_openclaw_state_home)"
    [[ -n "$oc_home_ob" ]] || oc_home_ob="${HOME:-}"
    ob_log="$(mktemp /tmp/opc200-openclaw-onboard-XXXXXX.log)"
    ok "onboard 完整日志: $ob_log"
    set +e
    (
        [[ -n "$v_anth" ]] && export ANTHROPIC_API_KEY="$v_anth"
        [[ -n "$v_openai" ]] && export OPENAI_API_KEY="$v_openai"
        [[ -n "$v_gemini" ]] && export GEMINI_API_KEY="$v_gemini"
        [[ -n "$v_custom_key" ]] && export CUSTOM_API_KEY="$v_custom_key"
        if ! $SILENT && [[ "$auth" == "custom-api-key" ]]; then
            export OPENCLAW_CUSTOM_BASE_URL="$v_custom_url"
            export OPENCLAW_CUSTOM_MODEL_ID="$v_custom_model"
        fi
        if command -v timeout &>/dev/null; then
            _openclaw_run "$oc_home_ob" timeout "$ob_deadline" openclaw "${oc_args[@]}"
        else
            _openclaw_run "$oc_home_ob" openclaw "${oc_args[@]}"
        fi
    ) 2>&1 | tee "$ob_log"
    exit_code=${PIPESTATUS[0]}
    set -e

    if [[ "$exit_code" -eq 124 ]]; then
        if [[ "${OPENCLAW_ONBOARD_STRICT:-}" == "1" ]]; then
            fail $E002 "E002: openclaw onboard 超时（>${ob_deadline}s）。可运行 openclaw doctor"
        fi
        warn "openclaw onboard 超时，已非严格继续。设置 OPENCLAW_ONBOARD_STRICT=1 可中止安装。"
        warn "onboard 日志末尾:"
        tail -n 40 "$ob_log" >&2 || true
        return 0
    fi
    if [[ "$exit_code" -ne 0 ]]; then
        if $use_onboard_daemon && [[ -f "$ob_log" ]] && grep -qiE 'systemd user services are unavailable|user services are not reachable|Gateway service install is unavailable.*systemd user|skipping service install' "$ob_log"; then
            warn "openclaw 未装上用户级网关服务（退出码 ${exit_code}），日志：$ob_log"
            tail -n 20 "$ob_log" >&2 || true
            _opc200_abort_user_systemd_setup "${SUDO_USER:-$(id -un)}"
        fi
        if [[ "${OPENCLAW_ONBOARD_STRICT:-}" == "1" ]]; then
            fail $E002 "E002: openclaw onboard 失败（退出码 ${exit_code}）。请运行 openclaw doctor；完整日志: $ob_log"
        fi
        warn "openclaw onboard 失败（退出码 ${exit_code}），已非严格继续。常见原因：密钥无效/网络；可设 OPENCLAW_SKIP_ONBOARD=1 跳过本步后手动 onboard。"
        warn "onboard 日志末尾（完整见 $ob_log）:"
        tail -n 50 "$ob_log" >&2 || true
        return 0
    fi

    if ! $SILENT; then
        case "$auth" in
            apiKey)       [[ -n "${v_anth:-}" ]] && export ANTHROPIC_API_KEY="$v_anth" ;;
            openai-api-key) [[ -n "${v_openai:-}" ]] && export OPENAI_API_KEY="$v_openai" ;;
            gemini-api-key) [[ -n "${v_gemini:-}" ]] && export GEMINI_API_KEY="$v_gemini" ;;
            custom-api-key)
                export OPENCLAW_CUSTOM_BASE_URL="$v_custom_url"
                export OPENCLAW_CUSTOM_MODEL_ID="$v_custom_model"
                [[ -n "${v_custom_key:-}" ]] && export CUSTOM_API_KEY="$v_custom_key"
                ;;
        esac
    fi
}

_set_openclaw_gateway_port_env() {
    local exe_hint="$1"
    local gw_hint="$2"
    local oc_home="${3:-}"
    [[ -n "$oc_home" ]] || oc_home="$(_openclaw_state_home)"
    local gp="$gw_hint"
    local pt
    pt="$(_openclaw_run "$oc_home" openclaw config get gateway.port 2>/dev/null | tr -d '\r\n"')" || true
    if [[ "$pt" =~ ^[0-9]+$ ]]; then
        gp="$pt"
    else
        warn "gateway.port 读取结果非数字（${pt:-空}），回退端口 $gw_hint"
    fi
    export OPENCLAW_GATEWAY_PORT="$gp"
    export OPENCLAW_GATEWAY_HEALTH_URL="http://127.0.0.1:${gp}/health"
    ok "已记录 gateway 端口 $gp（OPENCLAW_GATEWAY_PORT / OPENCLAW_GATEWAY_HEALTH_URL，供 opc-agent agent_health）"
}

_gateway_installed_heuristic() {
    local json="$1"
    [[ -z "$json" ]] && return 1
    if echo "$json" | grep -qiE '"installed"[[:space:]]*:[[:space:]]*true'; then return 0; fi
    if echo "$json" | grep -qiE 'not[[:space:]_-]*installed|not installed'; then return 1; fi
    return 0
}

step_openclaw_gateway_doctor_only() {
    local exe="$1"
    local oc_home="${2:-$(_openclaw_state_home)}"
    info "9/15 OpenClaw doctor 复查"
    local code=0
    _openclaw_run "$oc_home" openclaw doctor --non-interactive 2>&1 || code=$?
    if [[ "$code" -ne 0 ]]; then
        warn "openclaw doctor 返回非零（$code）；仍将继续安装 OPC200 Agent"
    else
        ok "openclaw doctor 完成"
    fi
}

step_openclaw_gateway_part2() {
    info "8/15 OpenClaw 网关配置"
    local rc=0
    _expand_path_for_openclaw_cli
    if ! command -v openclaw &>/dev/null; then
        warn "仍找不到 openclaw。若使用 sudo，可尝试: sudo env PATH=\"\$PATH\" NODE_BINARY=\"${NODE_BINARY:-}\" ./install.sh …"
        fail $E002 'E002: 第二部分需要 openclaw CLI，但未找到。请先完成官方安装或检查 PATH（npm 全局前缀下的 bin、~/.local/bin）。'
    fi
    local exe oc_home
    exe="$(command -v openclaw)"
    oc_home="$(_openclaw_state_home)"
    [[ -n "$oc_home" ]] || fail $E002 "E002: 无法确定 OpenClaw 配置家目录（HOME）"
    local gw_port="$OPENCLAW_DEFAULT_GATEWAY_PORT"
    if [[ "${OPENCLAW_GATEWAY_PORT:-}" =~ ^[0-9]+$ ]]; then
        gw_port="$OPENCLAW_GATEWAY_PORT"
    fi

    if $FRESH_OPENCLAW_CLI; then
        ok "本次为新安装 openclaw CLI；优先 RPC 探测，未就绪时再区分未安装/需修复。"
    fi

    if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
        _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
        ok "网关 RPC 探测正常，跳过安装/配置/启动"
        return 0
    fi

    warn "网关 RPC 未就绪；将检查 gateway 是否已安装"
    local st_json=""
    st_json="$(_openclaw_run "$oc_home" openclaw gateway status --json --no-probe 2>/dev/null)" || true
    local installed=false
    if _gateway_installed_heuristic "$st_json"; then
        installed=true
    else
        warn "gateway status --no-probe 不可用或解析失败，按未安装 gateway 服务处理"
    fi

    if $installed; then
        warn "服务已登记但 RPC 异常，将尝试配置并启动"
        ok "配置网关：gateway.mode=local"
        _openclaw_run "$oc_home" openclaw config set gateway.mode local || fail $E002 "E002: openclaw config set gateway.mode local 失败"
        _openclaw_run "$oc_home" openclaw config set gateway.tls.enabled false 2>/dev/null || warn "未能写入 gateway.tls.enabled=false（可忽略）"
        ok "应用网关：openclaw gateway restart"
        local rc=0
        _openclaw_run "$oc_home" openclaw gateway restart 2>&1 || rc=$?
        if [[ "$rc" -ne 0 ]]; then
            warn "gateway restart 返回 $rc；尝试 gateway start"
            _openclaw_run "$oc_home" openclaw gateway start 2>&1 || warn "gateway start 仍失败"
        fi
        sleep 2
        local i
        for i in $(seq 1 "$OPENCLAW_GATEWAY_WARMUP_MAX_TRIES"); do
            if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
                ok "网关 RPC 探测就绪（第 ${i}/${OPENCLAW_GATEWAY_WARMUP_MAX_TRIES} 次）"
                _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
                return 0
            fi
            if command -v curl &>/dev/null && curl -sf --connect-timeout 3 "http://127.0.0.1:${gw_port}/health" &>/dev/null; then
                ok "网关 HTTP /health 就绪（第 ${i}/${OPENCLAW_GATEWAY_WARMUP_MAX_TRIES} 次）"
                _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
                return 0
            fi
            sleep "$OPENCLAW_GATEWAY_WARMUP_SLEEP_SEC"
        done
        step_openclaw_gateway_doctor_only "$exe" "$oc_home"
        _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
        return 0
    fi

    local attempt=1
    local gi=1
    while [[ "$attempt" -le "$OPENCLAW_GW_INSTALL_MAX_RETRY" ]]; do
        ok "安装 gateway 服务（第 ${attempt}/${OPENCLAW_GW_INSTALL_MAX_RETRY}）：openclaw gateway install --port ${gw_port}"
        gi=0
        _openclaw_run "$oc_home" openclaw gateway install --port "$gw_port" 2>&1 || gi=$?
        if [[ "$gi" -eq 0 ]]; then
            ok "gateway install 成功"
            break
        fi
        warn "gateway install 失败（退出码 $gi），将重试"
        attempt=$((attempt + 1))
    done
    [[ "$gi" -eq 0 ]] || fail $E002 "E002: gateway install 在 ${OPENCLAW_GW_INSTALL_MAX_RETRY} 次重试后仍失败"

    ok "配置网关：gateway.mode=local"
    _openclaw_run "$oc_home" openclaw config set gateway.mode local || fail $E002 "E002: config set gateway.mode 失败"
    _openclaw_run "$oc_home" openclaw config set gateway.tls.enabled false 2>/dev/null || true
    ok "应用网关：openclaw gateway restart"
    rc=0
    _openclaw_run "$oc_home" openclaw gateway restart 2>&1 || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        _openclaw_run "$oc_home" openclaw gateway start 2>&1 || warn "gateway start 失败"
    fi
    sleep 2
    for i in $(seq 1 "$OPENCLAW_GATEWAY_WARMUP_MAX_TRIES"); do
        if _openclaw_run "$oc_home" openclaw gateway status --json --require-rpc &>/dev/null; then
            ok "网关 RPC 就绪"
            _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
            return 0
        fi
        if command -v curl &>/dev/null && curl -sf --connect-timeout 3 "http://127.0.0.1:${gw_port}/health" &>/dev/null; then
            ok "网关 HTTP 就绪"
            _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
            return 0
        fi
        sleep "$OPENCLAW_GATEWAY_WARMUP_SLEEP_SEC"
    done
    step_openclaw_gateway_doctor_only "$exe" "$oc_home"
    _set_openclaw_gateway_port_env "$exe" "$gw_port" "$oc_home"
}

_write_doc_template_from_file() {
    local source="$1"
    local target="$2"
    [[ -f "$source" ]] || fail $E001 "E001: 模板文件不存在: $source"
    if [[ -f "$target" ]]; then
        cp "$source" "${target}.new"
        warn "已存在，写入增量文件: ${target}.new"
    else
        cp "$source" "$target"
        ok "已写入模板: $target"
    fi
}

# ── Step 5: 下载 Agent ───────────────────────────────────────────

step_download() {
    if [[ -n "$LOCAL_BINARY" ]]; then
        info "11/15 使用本地二进制"
        [[ -f "$LOCAL_BINARY" ]] || fail $E001 "E001: 本地二进制不存在: $LOCAL_BINARY"
        TMP_BINARY="$LOCAL_BINARY"
        ok "使用本地二进制: $LOCAL_BINARY"
        return
    fi

    if $USE_PYTHON; then
        local reqfile="requirements-agent-runtime.txt"
        if $FULL_RUNTIME_DEPS; then
            reqfile="requirements-agent-runtime-full.txt"
            info "11/15 Python 运行环境 (venv + pip，完整依赖，体积大、耗时长)"
        else
            info "11/15 Python 运行环境 (venv + pip，精简依赖)"
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

    info "11/15 下载 Agent"

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

# ── Step 6: 安装部署 ─────────────────────────────────────────────

step_install() {
    info "12/15 安装部署"

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
  id: "${TENANT_ID}"

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

# ── Step 7: 注册系统服务 ─────────────────────────────────────────

step_register_service() {
    info "13/15 注册系统服务"

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

# ── Step 8: 启动验证 ─────────────────────────────────────────────

step_start_verify() {
    info "14/15 启动验证"

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

# ── Step 9: 完成输出 ─────────────────────────────────────────────

step_summary() {
    info "15/15 安装完成"

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
            --opc200-platform-url) PLATFORM_URL="$2"; shift 2 ;;
            --opc200-tenant-id)   TENANT_ID="$2"; shift 2 ;;
            --opc200-api-key)      API_KEY="$2"; shift 2 ;;
            --opc200-port)         PORT="$2"; shift 2 ;;
            --platform-url)        PLATFORM_URL="$2"; shift 2 ;;
            --customer-id)         TENANT_ID="$2"; shift 2 ;;
            --api-key)             API_KEY="$2"; shift 2 ;;
            --install-dir)         INSTALL_DIR="$2"; shift 2 ;;
            --port)                PORT="$2"; shift 2 ;;
            --local-binary)        LOCAL_BINARY="$2"; USE_PYTHON=false; shift 2 ;;
            --repo-root)           REPO_ROOT="$2"; shift 2 ;;
            --binary)              USE_PYTHON=false; shift ;;
            --full-runtime-deps)   FULL_RUNTIME_DEPS=true; shift ;;
            --openclaw-onboard)    OPENCLAW_ONBOARD_CLI=true; shift ;;
            --skip-openclaw-onboard) OPENCLAW_SKIP_ONBOARD_CLI=true; shift ;;
            --silent)              SILENT=true; shift ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo "  OPC200 段: --opc200-platform-url URL | --opc200-tenant-id ID | --opc200-api-key KEY | --opc200-port N"
                echo "  兼容旧名: --platform-url | --customer-id | --api-key | --port"
                echo "  目录/仓库: --install-dir DIR | --repo-root DIR"
                echo "  OpenClaw: --openclaw-onboard | --skip-openclaw-onboard | 环境变量 OPENCLAW_*（见 install.ps1 / README）"
                echo "  其他: --silent | --binary | --local-binary PATH | --full-runtime-deps"
                echo "默认: Python venv + 仓库源码；与 Windows install.ps1 分段一致。"
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

    step_initialize_paths
    step_check_env
    step_prepare_node_runtime
    step_network_check
    step_install_openclaw_official
    step_openclaw_onboard
    step_preinstall_openclaw_assets
    step_openclaw_gateway_part2
    step_openclaw_gateway_wsl_fallback
    step_opc200_platform_config
    step_download
    step_install
    step_register_service
    step_start_verify
    step_summary
}

parse_args "$@"
main