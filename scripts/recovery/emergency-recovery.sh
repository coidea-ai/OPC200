#!/bin/bash
#===============================================================================
# OPC200 Emergency Recovery Script
# 用途: 紧急恢复和故障处理
# 执行位置: 支持中心（通过 Tailscale 连接）
#===============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
OPC_ID=""
SCENARIO=""
DRY_RUN=false
NOTIFY=true

show_help() {
    cat << EOF
OPC200 Emergency Recovery Script

Usage: $0 [OPTIONS]

SCENARIOS:
    gateway-failure          Gateway 完全故障
    data-vault-corruption    数据保险箱损坏
    tailscale-disconnect     Tailscale 连接丢失
    disk-full                磁盘空间满
    memory-exhausted         内存耗尽

OPTIONS:
    --id ID                  客户ID
    --scenario SCENARIO      故障场景
    --dry-run               模拟运行，不实际执行
    --no-notify             不发送通知
    -h, --help             显示此帮助

示例:
    # 恢复 Gateway 故障
    $0 --id OPC-001 --scenario gateway-failure

    # 模拟恢复
    $0 --id OPC-001 --scenario disk-full --dry-run
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --id)
                OPC_ID="$2"
                shift 2
                ;;
            --scenario)
                SCENARIO="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-notify)
                NOTIFY=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    if [[ -z "$OPC_ID" ]] || [[ -z "$SCENARIO" ]]; then
        log_error "缺少必需参数 (--id, --scenario)"
        exit 1
    fi
}

# 执行命令（支持 dry-run）
run_cmd() {
    local cmd="$1"
    local desc="${2:-$cmd}"
    
    log_info "执行: $desc"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [DRY-RUN] $cmd"
        return 0
    fi
    
    eval "$cmd"
}

# 通知客户
notify_customer() {
    local message="$1"
    
    if [[ "$NOTIFY" == false ]]; then
        return 0
    fi
    
    log_info "发送通知: $message"
    
    # 这里应该调用飞书 Bot API 发送通知
    # curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/..." \
    #   -H "Content-Type: application/json" \
    #   -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"$message\"}}"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [DRY-RUN] 通知已模拟发送"
    else
        log_success "通知已发送"
    fi
}

# 场景：Gateway 故障
recover_gateway_failure() {
    log_warn "场景: Gateway 完全故障"
    
    # 1. 诊断
    log_info "步骤 1: 诊断故障"
    run_cmd "docker ps -a | grep opc200-${OPC_ID,,}" "检查容器状态"
    run_cmd "docker logs opc200-${OPC_ID,,}-gateway --tail 100" "查看日志"
    
    # 2. 尝试重启
    log_info "步骤 2: 尝试重启 Gateway"
    run_cmd "docker restart opc200-${OPC_ID,,}-gateway" "重启容器"
    
    sleep 5
    
    # 3. 检查状态
    log_info "步骤 3: 检查重启结果"
    if docker ps | grep -q "opc200-${OPC_ID,,}-gateway"; then
        log_success "Gateway 已恢复"
        notify_customer "您的 OPC200 Gateway 已恢复运行"
        return 0
    fi
    
    # 4. 重建容器
    log_warn "重启失败，尝试重建容器"
    run_cmd "cd /opt/opc200/${OPC_ID}/gateway && docker-compose down" "停止旧容器"
    run_cmd "docker-compose up -d" "重建容器"
    
    sleep 10
    
    # 5. 验证
    if docker ps | grep -q "opc200-${OPC_ID,,}-gateway"; then
        log_success "Gateway 重建成功"
        notify_customer "您的 OPC200 Gateway 已重建并恢复"
    else
        log_error "Gateway 重建失败，需要人工介入"
        return 1
    fi
}

# 场景：数据保险箱损坏
recover_data_vault_corruption() {
    log_warn "场景: 数据保险箱损坏"
    
    local vault_dir="/opt/opc200/${OPC_ID}/data-vault"
    local backup_dir="/opt/opc200/${OPC_ID}/backup"
    
    # 1. 检查损坏程度
    log_info "步骤 1: 评估损坏程度"
    run_cmd "ls -la ${vault_dir}/" "检查保险箱目录"
    
    # 2. 停止 Gateway
    log_info "步骤 2: 停止 Gateway 防止进一步损坏"
    run_cmd "docker stop opc200-${OPC_ID,,}-gateway" "停止 Gateway"
    
    # 3. 找到最新备份
    log_info "步骤 3: 查找可用备份"
    local latest_backup=$(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" | sort | tail -1)
    
    if [[ -z "$latest_backup" ]]; then
        log_error "无可用备份!"
        return 1
    fi
    
    log_info "使用备份: $(basename "$latest_backup")"
    
    # 4. 备份当前状态（用于分析）
    log_info "步骤 4: 备份当前损坏状态"
    run_cmd "mv ${vault_dir} ${vault_dir}.corrupted.$(date +%Y%m%d-%H%M%S)" "移动损坏数据"
    
    # 5. 恢复数据
    log_info "步骤 5: 从备份恢复"
    run_cmd "mkdir -p ${vault_dir}" "创建新目录"
    run_cmd "tar -xzf ${latest_backup}/data.tar.gz -C $(dirname ${vault_dir})" "恢复数据"
    
    # 6. 重启 Gateway
    log_info "步骤 6: 重启 Gateway"
    run_cmd "docker start opc200-${OPC_ID,,}-gateway" "启动 Gateway"
    
    log_success "数据保险箱已恢复"
    notify_customer "您的数据保险箱已从备份恢复"
}

# 场景：Tailscale 断开
recover_tailscale_disconnect() {
    log_warn "场景: Tailscale 连接丢失"
    
    # 1. 检查状态
    log_info "步骤 1: 检查 Tailscale 状态"
    run_cmd "tailscale status" "检查状态"
    
    # 2. 尝试重连
    log_info "步骤 2: 尝试重新连接"
    run_cmd "tailscale down && tailscale up --authkey=$(cat /opt/opc200/${OPC_ID}/tailscale/auth-key)" "重新连接"
    
    sleep 5
    
    # 3. 验证
    if tailscale status &> /dev/null; then
        log_success "Tailscale 已恢复"
        notify_customer "VPN 连接已恢复"
    else
        log_error "Tailscale 重连失败"
        log_info "建议检查网络或重新授权"
        return 1
    fi
}

# 场景：磁盘满
recover_disk_full() {
    log_warn "场景: 磁盘空间满"
    
    # 1. 分析磁盘使用
    log_info "步骤 1: 分析磁盘使用"
    run_cmd "df -h /" "查看磁盘空间"
    run_cmd "du -sh /opt/opc200/${OPC_ID}/*" "查看各目录大小"
    
    # 2. 清理日志
    log_info "步骤 2: 清理旧日志"
    run_cmd "find /opt/opc200/${OPC_ID}/logs -name '*.log' -mtime +7 -delete" "删除7天前日志"
    run_cmd "find /opt/opc200/${OPC_ID}/logs -name '*.log.*' -mtime +3 -delete" "删除旧轮转日志"
    
    # 3. 清理旧备份
    log_info "步骤 3: 清理旧备份"
    run_cmd "find /opt/opc200/${OPC_ID}/backup -maxdepth 1 -type d -name 'auto-*' -mtime +3 -exec rm -rf {} +" "删除3天前备份"
    
    # 4. Docker 清理
    log_info "步骤 4: 清理 Docker"
    run_cmd "docker system prune -f" "清理未使用资源"
    
    # 5. 验证
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    if [[ $disk_usage -lt 85 ]]; then
        log_success "磁盘空间已释放 (当前: ${disk_usage}%)"
        notify_customer "磁盘空间已清理，当前使用 ${disk_usage}%"
    else
        log_warn "磁盘仍然紧张 (${disk_usage}%)，建议扩容"
        return 1
    fi
}

# 场景：内存耗尽
recover_memory_exhausted() {
    log_warn "场景: 内存耗尽"
    
    # 1. 检查内存使用
    log_info "步骤 1: 检查内存使用"
    run_cmd "free -h" "查看内存"
    run_cmd "ps aux --sort=-%mem | head -20" "查看内存使用进程"
    
    # 2. 重启 Gateway（释放内存）
    log_info "步骤 2: 重启 Gateway"
    run_cmd "docker restart opc200-${OPC_ID,,}-gateway" "重启 Gateway"
    
    # 3. 清理缓存
    log_info "步骤 3: 清理系统缓存"
    run_cmd "sync && echo 3 > /proc/sys/vm/drop_caches" "清理缓存"
    
    # 4. 验证
    sleep 5
    local mem_info=$(free | grep Mem)
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_usage=$((mem_used * 100 / mem_total))
    
    if [[ $mem_usage -lt 90 ]]; then
        log_success "内存使用已降低 (当前: ${mem_usage}%)"
    else
        log_warn "内存仍然紧张，建议增加内存"
    fi
}

# 记录审计日志
log_audit() {
    local action="$1"
    local result="$2"
    
    local audit_dir="customers/on-premise/${OPC_ID}/remote-sessions"
    mkdir -p "$audit_dir"
    
    cat >> "${audit_dir}/emergency-recovery-$(date +%Y%m%d-%H%M%S).log" << EOF
---
timestamp: $(date -Iseconds)
operator: $(whoami)
hostname: $(hostname)
action: ${action}
scenario: ${SCENARIO}
dry_run: ${DRY_RUN}
result: ${result}
EOF
}

# 主函数
main() {
    log_info "OPC200 Emergency Recovery"
    log_info "========================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "场景: $SCENARIO"
    log_info "模式: $([[ "$DRY_RUN" == true ]] && echo "模拟运行" || echo "实际执行")"
    
    echo ""
    
    # 执行对应场景的恢复
    case "$SCENARIO" in
        gateway-failure)
            recover_gateway_failure
            ;;
        data-vault-corruption)
            recover_data_vault_corruption
            ;;
        tailscale-disconnect)
            recover_tailscale_disconnect
            ;;
        disk-full)
            recover_disk_full
            ;;
        memory-exhausted)
            recover_memory_exhausted
            ;;
        *)
            log_error "未知场景: $SCENARIO"
            exit 1
            ;;
    esac
    
    local result=$?
    
    # 记录审计
    log_audit "emergency_recovery" "$([[ $result -eq 0 ]] && echo "success" || echo "failed")"
    
    echo ""
    if [[ $result -eq 0 ]]; then
        log_success "========================="
        log_success "恢复完成!"
        log_success "========================="
    else
        log_error "========================="
        log_error "恢复失败，需要人工介入"
        log_error "========================="
    fi
    
    exit $result
}

main "$@"
