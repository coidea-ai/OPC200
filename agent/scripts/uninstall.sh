#!/usr/bin/env bash
# AGENT-003: OPC200 Agent Mac/Linux 卸载脚本
set -euo pipefail

INSTALL_DIR="${HOME}/.opc200"
SERVICE_NAME="opc200-agent"
KEEP_DATA=false
SILENT=false
OS_TYPE=""

info()  { printf "\033[36m[INFO] %s\033[0m\n" "$*"; }
ok()    { printf "\033[32m  [OK] %s\033[0m\n" "$*"; }
warn()  { printf "\033[33m [WARN] %s\033[0m\n" "$*"; }
err()   { printf "\033[31m  [ERR] %s\033[0m\n" "$*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --keep-data)   KEEP_DATA=true; shift ;;
        --silent)      SILENT=true; shift ;;
        -h|--help)
            echo "用法: $0 [--install-dir DIR] [--keep-data] [--silent]"
            exit 0
            ;;
        *) err "未知参数: $1"; exit 1 ;;
    esac
done

OS_TYPE="$(uname -s | tr '[:upper:]' '[:lower:]')"

if [[ $EUID -ne 0 ]] && [[ "$OS_TYPE" == "linux" ]]; then
    err "请以 root 或 sudo 运行"; exit 1
fi

info "OPC200 Agent 卸载"

# Step 1: 停止服务
info "停止服务..."
if [[ "$OS_TYPE" == "linux" ]]; then
    systemctl stop "$SERVICE_NAME" 2>/dev/null && ok "systemd 服务已停止" || warn "服务未运行或不存在"
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload 2>/dev/null || true
    ok "systemd 服务已移除"
elif [[ "$OS_TYPE" == "darwin" ]]; then
    local_plist="${HOME}/Library/LaunchAgents/co.opc200.agent.plist"
    if [[ -f "$local_plist" ]]; then
        launchctl unload "$local_plist" 2>/dev/null && ok "launchd 服务已卸载" || warn "服务未加载"
        rm -f "$local_plist"
    else
        warn "未找到 plist"
    fi
fi

# Step 2: 删除文件
if [[ ! -d "$INSTALL_DIR" ]]; then
    warn "安装目录不存在: $INSTALL_DIR"
    exit 0
fi

if ! $SILENT; then
    read -rp "确认删除 ${INSTALL_DIR}？[y/N] " ans
    [[ "$ans" =~ ^[Yy] ]] || { info "已取消"; exit 0; }
fi

if $KEEP_DATA; then
    info "保留 data/ 目录"
    for d in bin config logs; do
        rm -rf "${INSTALL_DIR:?}/$d"
    done
    rm -f "${INSTALL_DIR}/.env" "${INSTALL_DIR}/config/config.yml"
    ok "已删除（保留 data/）"
else
    rm -rf "${INSTALL_DIR:?}"
    ok "已完全删除 $INSTALL_DIR"
fi

echo ""
ok "OPC200 Agent 已卸载"
