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
OPENCLAW_MIN_NODE_MAJOR=22
OPENCLAW_DEFAULT_NPM_REGISTRY="https://registry.npmmirror.com/"
OPENCLAW_INSTALL_TIMEOUT_SEC=900
OPENCLAW_NET_CHECK_HOSTS=("openclaw.ai" "registry.npmmirror.com" "github.com")
OPENCLAW_DEFAULT_PROFILE_DIR="$HOME/.openclaw"
OPENCLAW_DEFAULT_SKILLS="skill-vetter"
OPENCLAW_DEFAULT_SKILL_INSTALL_CMD="openclaw skills install"
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
    info "1/10 环境检查"

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
    info "2/10 获取配置"

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

# ── Step 3: 准备 Node.js（Linux）──────────────────────────────────

get_node_major_version() {
    if ! command -v node &>/dev/null; then
        echo "0"
        return
    fi
    local ver
    ver="$(node -v 2>/dev/null || true)"
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

    local page tarball url tmpdir extracted
    page="$(curl -fsSL "https://nodejs.org/dist/latest-v22.x/" 2>/dev/null)" || fail $E002 "E002: 无法访问 nodejs.org（下载 Node 22）"
    tarball="$(printf '%s\n' "$page" | sed -n "s/.*href=\"\\(node-v22[^\"]*-linux-${node_arch}\\.tar\\.xz\\)\".*/\\1/p" | head -n1)"
    [[ -n "$tarball" ]] || fail $E002 "E002: 未找到 Node 22 Linux 安装包（架构 ${node_arch}）"
    url="https://nodejs.org/dist/latest-v22.x/${tarball}"

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
    info "3/10 准备 Node.js（OpenClaw 需要 v${OPENCLAW_MIN_NODE_MAJOR}+）"

    if [[ "$OS_TYPE" != "linux" ]]; then
        ok "当前非 Linux，跳过 Node.js 预安装步骤"
        return
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
    info "3.5/10 网络连通性预检"
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
        warn "部分主机不可达；若安装超时，可设置 OPENCLAW_NPM_REGISTRY 指向可用镜像后重试"
    fi
}

# ── Step 4: 官方渠道安装 OpenClaw latest ─────────────────────────

step_install_openclaw_official() {
    info "4/10 官方渠道安装 OpenClaw latest"

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

    # npm registry：优先使用环境变量，默认淘宝镜像加速
    local npm_registry="${OPENCLAW_NPM_REGISTRY:-$OPENCLAW_DEFAULT_NPM_REGISTRY}"

    ok "OpenClaw 安装源: $install_url"
    ok "OpenClaw 渠道: $channel"
    ok "npm registry: $npm_registry"

    # 实时输出 + 超时控制：通过 tee 落日志，timeout 命令限制最长执行时间
    local log_file
    log_file="$(mktemp /tmp/opc200-openclaw-install-XXXXXX.log)"
    ok "安装日志: $log_file"

    local exit_code=0
    NPM_CONFIG_REGISTRY="$npm_registry" \
    NPM_CONFIG_FETCH_RETRIES="3" \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT="10000" \
    NPM_CONFIG_FETCH_TIMEOUT="60000" \
    NODE_LLAMA_CPP_SKIP_DOWNLOAD="1" \
    OPENCLAW_NO_ONBOARD="1" \
        timeout "$OPENCLAW_INSTALL_TIMEOUT_SEC" \
        bash -c "curl -fsSL '$install_url' | bash" \
        2>&1 | tee "$log_file" || exit_code=${PIPESTATUS[0]}

    if [[ "$exit_code" -eq 124 ]]; then
        fail $E002 "E002: OpenClaw 官方安装超时（>${OPENCLAW_INSTALL_TIMEOUT_SEC}s）。日志: $log_file"
    elif [[ "$exit_code" -ne 0 ]]; then
        fail $E002 "E002: OpenClaw 官方安装失败（退出码 ${exit_code}）。日志: $log_file"
    fi

    ok "OpenClaw 官方安装完成"
}

# ── Step 5: 轻预装层（skills + 文档）────────────────────────────

step_preinstall_openclaw_assets() {
    info "5/10 轻预装层（skills + 文档）"

    local profile_dir="${OPENCLAW_PROFILE_DIR:-$OPENCLAW_DEFAULT_PROFILE_DIR}"
    local skills_csv="${OPENCLAW_PREINSTALL_SKILLS:-$OPENCLAW_DEFAULT_SKILLS}"
    local skill_install_cmd="${OPENCLAW_SKILL_INSTALL_CMD:-$OPENCLAW_DEFAULT_SKILL_INSTALL_CMD}"
    local failed=0
    local templates_dir="$SCRIPT_DIR/openclaw-templates"

    mkdir -p "$profile_dir"
    ok "OpenClaw 配置目录: $profile_dir"

    # skills 安装失败按策略仅告警，不中断安装流程。
    if [[ -n "$skills_csv" ]]; then
        IFS=',' read -r -a skills <<< "$skills_csv"
        for skill in "${skills[@]}"; do
            skill="$(printf '%s' "$skill" | xargs)"
            [[ -z "$skill" ]] && continue
            if eval "$skill_install_cmd \"$skill\""; then
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
        info "6/10 使用本地二进制"
        [[ -f "$LOCAL_BINARY" ]] || fail $E001 "E001: 本地二进制不存在: $LOCAL_BINARY"
        TMP_BINARY="$LOCAL_BINARY"
        ok "使用本地二进制: $LOCAL_BINARY"
        return
    fi

    if $USE_PYTHON; then
        local reqfile="requirements-agent-runtime.txt"
        if $FULL_RUNTIME_DEPS; then
            reqfile="requirements-agent-runtime-full.txt"
            info "6/10 Python 运行环境 (venv + pip，完整依赖，体积大、耗时长)"
        else
            info "6/10 Python 运行环境 (venv + pip，精简依赖)"
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

    info "6/10 下载 Agent"

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
    info "7/10 安装部署"

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

# ── Step 7: 注册系统服务 ─────────────────────────────────────────

step_register_service() {
    info "8/10 注册系统服务"

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

# ── Step 8: 启动验证 ─────────────────────────────────────────────

step_start_verify() {
    info "9/10 启动验证"

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
    info "10/10 安装完成"

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
    step_prepare_node_runtime
    step_network_check
    step_install_openclaw_official
    step_preinstall_openclaw_assets
    step_download
    step_install
    step_register_service
    step_start_verify
    step_summary
}

parse_args "$@"
main
