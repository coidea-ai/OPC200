#!/usr/bin/env bash
# OPC200 Agent Mac/Linux 卸载脚本 — 与 uninstall.ps1 行为对齐
set -euo pipefail

INSTALL_DIR="${HOME}/.opc200"
SERVICE_NAME="opc200-agent"
KEEP_DATA=false
SILENT=false
KEEP_OPENCLAW_FLAG=false
PURGE_OPENCLAW_LEGACY=false
SHOULD_KEEP_OPENCLAW=false
OS_TYPE=""
EXPLICIT_INSTALL_DIR=false
OPENCLAW_DEFAULT_GATEWAY_PORT=18789

info()  { printf "\033[36m[STEP] %s\033[0m\n" "$*"; }
ok()    { printf "\033[32m  [OK] %s\033[0m\n" "$*"; }
warn()  { printf "\033[33m [WARN] %s\033[0m\n" "$*"; }
err()   { printf "\033[31m  [ERR] %s\033[0m\n" "$*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-dir) INSTALL_DIR="$2"; EXPLICIT_INSTALL_DIR=true; shift 2 ;;
        --keep-data)   KEEP_DATA=true; shift ;;
        --silent)      SILENT=true; shift ;;
        --keep-openclaw) KEEP_OPENCLAW_FLAG=true; shift ;;
        --purge-openclaw) PURGE_OPENCLAW_LEGACY=true; shift ;;
        -h|--help)
            echo "用法: $0 [--install-dir DIR] [--keep-data] [--silent] [--keep-openclaw]"
            echo "  --keep-openclaw   保留本机 OpenClaw（与 uninstall.ps1 -KeepOpenClaw 一致）"
            echo "  静默: 未指定 --keep-openclaw 时将尝试卸载 OpenClaw（先停 gateway，再 openclaw uninstall）"
            echo "  兼容: --purge-openclaw 等价于要卸载 OpenClaw（旧参数，不推荐）"
            exit 0
            ;;
        *) err "未知参数: $1"; exit 1 ;;
    esac
done

OS_TYPE="$(uname -s | tr '[:upper:]' '[:lower:]')"

if [[ $EUID -ne 0 ]] && [[ "$OS_TYPE" == "linux" ]]; then
    err "请以 root 或 sudo 运行"
    exit 1
fi

infer_install_dir_from_systemd_unit() {
    local unit="$1" line exe bin_dir
    [[ -f "$unit" ]] || return 1
    line="$(grep -m1 '^ExecStart=' "$unit" 2>/dev/null)" || return 1
    line="${line#ExecStart=}"
    line="${line#\"}"
    exe="${line%% *}"
    exe="${exe%%\"}"
    [[ -n "$exe" ]] || return 1
    bin_dir="$(dirname "$exe")"
    [[ "$(basename "$bin_dir")" == "bin" ]] || return 1
    dirname "$bin_dir"
}

UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
if [[ "$OS_TYPE" == "linux" ]] && [[ -f "$UNIT_PATH" ]] && ! $EXPLICIT_INSTALL_DIR; then
    if [[ ! -d "$INSTALL_DIR" ]]; then
        inferred="$(infer_install_dir_from_systemd_unit "$UNIT_PATH" || true)"
        if [[ -n "$inferred" && -d "$inferred" ]]; then
            INSTALL_DIR="$inferred"
            info "已从 systemd 单元推断安装目录: $INSTALL_DIR"
        fi
    fi
fi

resolve_keep_openclaw_choice() {
    if $KEEP_OPENCLAW_FLAG; then
        SHOULD_KEEP_OPENCLAW=true
        ok "已选择：保留 OpenClaw（--keep-openclaw）"
        return 0
    fi
    if $PURGE_OPENCLAW_LEGACY; then
        SHOULD_KEEP_OPENCLAW=false
        ok "已选择：卸载 OpenClaw（兼容 --purge-openclaw）"
        return 0
    fi
    if $SILENT; then
        SHOULD_KEEP_OPENCLAW=false
        ok "静默模式：未指定 --keep-openclaw，将尝试卸载 OpenClaw（若存在 CLI）"
        return 0
    fi
    echo ""
    echo "OpenClaw 是否与 OPC200 一并处理（必填）" >&2
    local ans=""
    while true; do
        read -rp "是否保留本机已安装的 OpenClaw？(Y=保留 / N=全部卸载) " ans || true
        case "$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]')" in
            y|yes)
                SHOULD_KEEP_OPENCLAW=true
                ok "已选择：保留 OpenClaw"
                break
                ;;
            n|no)
                SHOULD_KEEP_OPENCLAW=false
                ok "已选择：将卸载 OpenClaw（在 OPC200 目录删除之后执行）"
                break
                ;;
            *)
                err "请输入 Y 或 N"
                ;;
        esac
    done
}

get_openclaw_gateway_port() {
    local gw="$OPENCLAW_DEFAULT_GATEWAY_PORT"
    local pt
    pt="$(openclaw config get gateway.port 2>/dev/null | tr -d '\r\n\"')" || true
    if [[ "$pt" =~ ^[0-9]+$ ]]; then
        gw="$pt"
    fi
    printf '%s' "$gw"
}

port_is_listening() {
    local p="$1"
    if command -v ss &>/dev/null; then
        ss -tln 2>/dev/null | grep -q ":${p} " && return 0
    fi
    if command -v lsof &>/dev/null; then
        lsof -iTCP:"$p" -sTCP:LISTEN &>/dev/null && return 0
    fi
    return 1
}

stop_openclaw_gateway_before_uninstall() {
    local exe
    exe="$(command -v openclaw)" || { warn "未找到 openclaw 命令（PATH），跳过 gateway 停止"; return 0; }

    local gw
    gw="$(get_openclaw_gateway_port)"
    ok "OpenClaw gateway 端口（配置或默认）: $gw"

    local rpc_ok=false
    if openclaw gateway status --json --require-rpc &>/dev/null; then
        rpc_ok=true
    fi
    local listening=false
    if port_is_listening "$gw"; then
        listening=true
    fi

    if ! $rpc_ok && ! $listening; then
        ok "未发现运行中的 gateway（RPC 不可用且端口未监听），跳过 gateway stop"
        return 0
    fi

    warn "正在停止 OpenClaw gateway（openclaw gateway stop）..."
    openclaw gateway stop 2>/dev/null || true
    sleep 2

    local i
    for i in $(seq 1 15); do
        if ! port_is_listening "$gw"; then
            ok "端口 $gw 已释放"
            return 0
        fi
        sleep 2
    done

    if command -v ss &>/dev/null; then
        local pids
        pids="$(ss -tlnp 2>/dev/null | grep ":${gw} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | sort -u)" || true
        for pid in $pids; do
            [[ -n "$pid" ]] || continue
            warn "强制结束仍占用端口 $gw 的进程 PID=$pid"
            kill -9 "$pid" 2>/dev/null || true
        done
    fi
    sleep 2
    ok "已尝试释放端口 $gw"
}

echo ""
echo "OPC200 Agent Uninstaller (Mac/Linux)"
echo ""

resolve_keep_openclaw_choice

TOTAL_STEPS=3
if ! $SHOULD_KEEP_OPENCLAW; then
    TOTAL_STEPS=4
fi

info "1/${TOTAL_STEPS} 停止并移除 OPC200 服务 / launchd"
if [[ "$OS_TYPE" == "linux" ]]; then
    systemctl stop "$SERVICE_NAME" 2>/dev/null && ok "systemd 服务已停止" || warn "服务未运行或不存在"
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload 2>/dev/null || true
    ok "systemd 单元已移除"
elif [[ "$OS_TYPE" == "darwin" ]]; then
    local_plist="${HOME}/Library/LaunchAgents/co.opc200.agent.plist"
    if [[ -f "$local_plist" ]]; then
        launchctl unload "$local_plist" 2>/dev/null && ok "launchd 已卸载" || warn "服务未加载"
        rm -f "$local_plist"
    else
        warn "未找到 plist"
    fi
fi

info "2/${TOTAL_STEPS} 清理 OPC200 安装目录"
if [[ ! -d "$INSTALL_DIR" ]]; then
    warn "安装目录不存在: $INSTALL_DIR（可能已手动删除），跳过文件清理"
    if [[ "$OS_TYPE" == "linux" ]]; then
        for c in "/root/.opc200" "/home/${SUDO_USER:-}/.opc200"; do
            [[ -d "$c" ]] && warn "若曾用 sudo 安装，可尝试: sudo $0 --install-dir '$c'"
        done
    fi
else
    if ! $SILENT; then
        read -rp "确认删除 ${INSTALL_DIR}？[y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] || { info "已取消"; exit 0; }
    fi

    if $KEEP_DATA; then
        info "保留 data/ 目录"
        for d in bin config logs venv; do
            rm -rf "${INSTALL_DIR:?}/$d"
        done
        rm -f "${INSTALL_DIR}/.env" "${INSTALL_DIR}/config/config.yml" "${INSTALL_DIR}/runtime.env" 2>/dev/null || true
        ok "已删除（保留 data/）"
    else
        rm -rf "${INSTALL_DIR:?}"
        ok "已完全删除 $INSTALL_DIR"
    fi
fi

if ! $SHOULD_KEEP_OPENCLAW; then
    info "3/${TOTAL_STEPS} 卸载 OpenClaw（先停 gateway，再执行官方卸载）"
    ok "进度 1/3：检查 openclaw 命令"
    if ! command -v openclaw &>/dev/null; then
        warn "未找到 openclaw 命令（PATH），无法自动停止 gateway 或执行官方卸载；若仍需移除，请手动删除 ~/.openclaw 并清理 npm 全局包"
    else
        oc_exe="$(command -v openclaw)"
        ok "进度 2/3：若 gateway 在运行则先停止并释放端口"
        stop_openclaw_gateway_before_uninstall
        ok "进度 3/3：openclaw uninstall --all --yes --non-interactive"
        openclaw uninstall --all --yes --non-interactive || warn "OpenClaw 卸载命令失败（已忽略，OPC200 已清理）"
        ok "OpenClaw 官方卸载命令已执行（CLI 全局包需自行 npm/pnpm 移除）"
    fi
fi

info "${TOTAL_STEPS}/${TOTAL_STEPS} 卸载完成"
echo ""
ok "OPC200 Agent 已卸载（自动启动已移除；目录已清空或本就不存在）"
