#!/bin/bash
#===============================================================================
# OPC200 Emergency Recovery Script
# 用途: 紧急恢复和故障处理
# 执行位置: 支持中心（通过 Tailscale 连接）
#===============================================================================

set -euo pipefail

# Source common logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"

# Default configuration
OPC_ID=""
SCENARIO=""
NOTIFY=true

# Available scenarios
SCENARIOS=(
    "gateway-failure"
    "data-vault-corruption"
    "tailscale-disconnect"
    "disk-full"
    "memory-exhausted"
    "service-unavailable"
)

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
    service-unavailable      服务不可用

OPTIONS:
    --id ID                  客户ID (必需)
    --scenario SCENARIO      故障场景 (必需)
    --dry-run                模拟运行，不实际执行
    --no-notify              不发送通知
    -v, --verbose            启用调试日志
    -h, --help               显示此帮助

示例:
    # 恢复 Gateway 故障
    $0 --id OPC-001 --scenario gateway-failure

    # 模拟恢复
    $0 --id OPC-001 --scenario disk-full --dry-run

    # 详细日志输出
    $0 --id OPC-001 --scenario memory-exhausted -v
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
                export OPC_DRY_RUN="true"
                log_warn "Dry run mode enabled - no changes will be made"
                shift
                ;;
            --no-notify)
                NOTIFY=false
                shift
                ;;
            -v|--verbose)
                export OPC_LOG_LEVEL="DEBUG"
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
        show_help
        exit 1
    fi
    
    # Validate scenario
    local valid_scenario=false
    for s in "${SCENARIOS[@]}"; do
        if [[ "$s" == "$SCENARIO" ]]; then
            valid_scenario=true
            break
        fi
    done
    
    if [[ "$valid_scenario" == false ]]; then
        log_error "未知场景: $SCENARIO"
        log_info "可用场景: ${SCENARIOS[*]}"
        exit 1
    fi
}

# Execute command with retry and dry-run support
run_cmd() {
    local cmd="$1"
    local desc="${2:-$cmd}"
    local max_retries="${3:-1}"
    local retry_delay="${4:-2}"
    
    log_info "执行: $desc"
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] $cmd"
        return 0
    fi
    
    local attempt=1
    while [[ $attempt -le $max_retries ]]; do
        log_debug "尝试 $attempt/$max_retries: $cmd"
        
        if eval "$cmd"; then
            log_debug "命令成功执行"
            return 0
        fi
        
        local exit_code=$?
        if [[ $attempt -lt $max_retries ]]; then
            log_warn "命令失败 (exit: $exit_code)，${retry_delay}秒后重试..."
            sleep $retry_delay
            retry_delay=$((retry_delay * 2))  # Exponential backoff
        fi
        ((attempt++))
    done
    
    log_error "命令在 $max_retries 次尝试后仍然失败"
    return 1
}

# Notify customer
notify_customer() {
    local message="$1"
    local severity="${2:-info}"  # info, warning, error
    
    if [[ "$NOTIFY" == false ]]; then
        log_debug "通知已禁用"
        return 0
    fi
    
    log_info "发送通知: $message"
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] 通知已模拟发送"
        return 0
    fi
    
    # TODO: Implement actual notification via Feishu Bot API
    # Example:
    # local webhook_url="${FEISHU_WEBHOOK_URL:-}"
    # if [[ -n "$webhook_url" ]]; then
    #     curl -X POST "$webhook_url" \
    #         -H "Content-Type: application/json" \
    #         -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"[$OPC_ID] $message\"}}" \
    #         --silent --show-error
    # fi
    
    log_debug "通知功能待实现 (需要配置飞书 Webhook)"
}

# Scenario: Gateway failure
recover_gateway_failure() {
    log_warn "场景: Gateway 完全故障"
    
    local container_name="opc200-${OPC_ID,,}-gateway"
    
    # Step 1: Diagnose
    log_info "步骤 1: 诊断故障"
    run_cmd "docker ps -a --filter name=$container_name --format '{{.Names}}: {{.Status}}'" "检查容器状态"
    run_cmd "docker logs $container_name --tail 50" "查看最近日志" 1 0 || log_warn "无法获取日志"
    run_cmd "docker inspect $container_name --format='{{.State.Health.Status}}' 2>/dev/null || echo 'N/A'" "检查健康状态"
    
    # Step 2: Try restart
    log_info "步骤 2: 尝试重启 Gateway"
    if run_cmd "docker restart $container_name" "重启容器" 3 2; then
        sleep 5
        
        # Step 3: Verify
        log_info "步骤 3: 检查重启结果"
        if docker ps --filter "name=$container_name" --filter "status=running" --format '{{.Names}}' | grep -q "$container_name"; then
            log_success "Gateway 已恢复运行"
            notify_customer "Gateway 重启成功，服务已恢复" "info"
            return 0
        fi
    fi
    
    # Step 4: Check if container exists
    log_warn "重启失败，检查容器状态..."
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        log_error "容器不存在，需要重新部署"
        notify_customer "Gateway 容器丢失，需要人工介入重新部署" "error"
        return 1
    fi
    
    # Step 5: Try recreate
    log_warn "尝试重建容器..."
    local compose_file="/opt/opc200/${OPC_ID}/gateway/docker-compose.yml"
    
    if [[ -f "$compose_file" ]]; then
        run_cmd "cd /opt/opc200/${OPC_ID}/gateway && docker-compose down" "停止旧容器" 2 1
        run_cmd "cd /opt/opc200/${OPC_ID}/gateway && docker-compose up -d" "重建容器" 2 3
        
        sleep 10
        
        # Verify
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            log_success "Gateway 重建成功"
            notify_customer "Gateway 已重建并恢复运行" "info"
            return 0
        fi
    else
        log_error "Compose 文件不存在: $compose_file"
    fi
    
    log_error "Gateway 恢复失败，需要人工介入"
    notify_customer "Gateway 故障无法自动恢复，需要紧急人工处理" "error"
    return 1
}

# Scenario: Data vault corruption
recover_data_vault_corruption() {
    log_warn "场景: 数据保险箱损坏"
    
    local vault_dir="/opt/opc200/${OPC_ID}/data-vault"
    local backup_dir="/opt/opc200/${OPC_ID}/backup"
    local container_name="opc200-${OPC_ID,,}-gateway"
    
    # Step 1: Check corruption level
    log_info "步骤 1: 评估损坏程度"
    if [[ -d "$vault_dir" ]]; then
        run_cmd "ls -la ${vault_dir}/" "检查保险箱目录"
        run_cmd "df -h ${vault_dir}" "检查磁盘空间"
    else
        log_warn "保险箱目录不存在: $vault_dir"
    fi
    
    # Step 2: Stop Gateway
    log_info "步骤 2: 停止 Gateway 防止进一步损坏"
    run_cmd "docker stop $container_name" "停止 Gateway" 2 1 || log_warn "Gateway 可能已经停止"
    
    # Step 3: Find latest backup
    log_info "步骤 3: 查找可用备份"
    local latest_backup=""
    
    if [[ -d "$backup_dir" ]]; then
        latest_backup=$(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" | sort | tail -1)
    fi
    
    if [[ -z "$latest_backup" ]]; then
        log_error "无可用备份!"
        notify_customer "数据保险箱损坏且无可用备份，情况紧急！" "error"
        return 1
    fi
    
    log_info "使用备份: $(basename "$latest_backup")"
    
    # Verify backup integrity
    local manifest="${latest_backup}/manifest.yml"
    if [[ -f "$manifest" ]]; then
        log_info "备份清单存在，验证完整性..."
        # TODO: Implement checksum verification
    else
        log_warn "备份无清单文件"
    fi
    
    # Step 4: Backup current corrupted state
    log_info "步骤 4: 备份当前损坏状态用于分析"
    local corrupted_backup="${vault_dir}.corrupted.$(date +%Y%m%d-%H%M%S)"
    if [[ -d "$vault_dir" ]]; then
        run_cmd "mv ${vault_dir} ${corrupted_backup}" "移动损坏数据"
    fi
    
    # Step 5: Restore from backup
    log_info "步骤 5: 从备份恢复"
    run_cmd "mkdir -p ${vault_dir}" "创建新目录"
    
    # Decrypt if needed
    if [[ -f "${latest_backup}/data.tar.gz.gpg" ]]; then
        log_info "解密备份数据..."
        local key_file="/opt/opc200/${OPC_ID}/data-vault/encrypted/keys/backup-key"
        if [[ -f "$key_file" ]]; then
            run_cmd "gpg --decrypt --passphrase-file $key_file --batch --yes -o ${latest_backup}/data.tar.gz ${latest_backup}/data.tar.gz.gpg" "解密备份"
        else
            log_error "解密密钥不存在"
            return 1
        fi
    fi
    
    # Extract backup
    if [[ -f "${latest_backup}/data.tar.gz" ]]; then
        run_cmd "tar -xzf ${latest_backup}/data.tar.gz -C $(dirname ${vault_dir})" "恢复数据"
    else
        log_error "备份数据文件不存在"
        return 1
    fi
    
    # Step 6: Restart Gateway
    log_info "步骤 6: 重启 Gateway"
    run_cmd "docker start $container_name" "启动 Gateway" 3 2
    
    # Verify
    sleep 5
    if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
        log_success "数据保险箱已恢复"
        notify_customer "数据保险箱已从备份恢复，服务正常运行" "info"
        return 0
    else
        log_error "Gateway 启动失败"
        return 1
    fi
}

# Scenario: Tailscale disconnect
recover_tailscale_disconnect() {
    log_warn "场景: Tailscale 连接丢失"
    
    # Step 1: Check status
    log_info "步骤 1: 检查 Tailscale 状态"
    run_cmd "tailscale status" "检查状态" 1 0 || true
    run_cmd "tailscale ip -4" "获取 Tailscale IP" 1 0 || true
    
    # Step 2: Check network
    log_info "检查网络连接..."
    run_cmd "ip route | grep tailscale" "检查路由表" 1 0 || true
    
    # Step 3: Try reconnect
    log_info "步骤 2: 尝试重新连接"
    local auth_key_file="/opt/opc200/${OPC_ID}/tailscale/auth-key"
    
    if [[ -f "$auth_key_file" ]]; then
        local auth_key=$(cat "$auth_key_file")
        run_cmd "tailscale down" "断开当前连接" 2 1 || true
        run_cmd "tailscale up --authkey=$auth_key --accept-routes" "重新连接" 3 5
    else
        log_warn "Auth key 文件不存在，尝试无密钥重连..."
        run_cmd "tailscale up --accept-routes" "尝试重连" 2 3
    fi
    
    # Step 4: Verify
    sleep 5
    if run_cmd "tailscale status" "验证连接状态"; then
        log_success "Tailscale 已恢复"
        notify_customer "VPN 连接已恢复" "info"
    else
        log_error "Tailscale 重连失败"
        log_info "建议检查网络或重新授权"
        notify_customer "VPN 连接无法恢复，可能需要重新授权" "warning"
        return 1
    fi
}

# Scenario: Disk full
recover_disk_full() {
    log_warn "场景: 磁盘空间满"
    
    local threshold=85
    
    # Step 1: Analyze disk usage
    log_info "步骤 1: 分析磁盘使用"
    run_cmd "df -h /" "查看根分区"
    run_cmd "df -h /opt/opc200/${OPC_ID}" "查看数据分区" 1 0 || true
    
    # Show top directories
    log_info "大目录分析..."
    run_cmd "du -sh /opt/opc200/${OPC_ID}/* 2>/dev/null | sort -hr | head -10" "查看各目录大小"
    
    # Step 2: Clean logs
    log_info "步骤 2: 清理旧日志"
    local log_dirs=(
        "/opt/opc200/${OPC_ID}/logs"
        "/var/log"
        "/opt/opc200/${OPC_ID}/gateway/logs"
    )
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            run_cmd "find $log_dir -name '*.log' -mtime +7 -type f -delete" "删除7天前日志"
            run_cmd "find $log_dir -name '*.log.*' -mtime +3 -type f -delete" "删除旧轮转日志"
        fi
    done
    
    # Step 3: Clean old backups
    log_info "步骤 3: 清理旧备份"
    local backup_dir="/opt/opc200/${OPC_ID}/backup"
    if [[ -d "$backup_dir" ]]; then
        # Keep only last 3 backups
        local backups_to_delete=$(find "$backup_dir" -maxdepth 1 -type d -name 'auto-*' | sort | head -n -3)
        if [[ -n "$backups_to_delete" ]]; then
            echo "$backups_to_delete" | while read -r backup; do
                run_cmd "rm -rf $backup" "删除旧备份: $(basename $backup)"
            done
        fi
    fi
    
    # Step 4: Docker cleanup
    log_info "步骤 4: 清理 Docker"
    run_cmd "docker system prune -f" "清理未使用资源"
    run_cmd "docker volume prune -f" "清理未使用卷" 1 0 || true
    
    # Step 5: Check result
    log_info "步骤 5: 验证清理结果"
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    
    if [[ $disk_usage -lt $threshold ]]; then
        log_success "磁盘空间已释放 (当前: ${disk_usage}%)"
        notify_customer "磁盘空间已清理，当前使用 ${disk_usage}%" "info"
    else
        log_warn "磁盘仍然紧张 (${disk_usage}%)，建议扩容"
        notify_customer "磁盘清理后仍紧张 (${disk_usage}%)，建议考虑扩容" "warning"
        return 1
    fi
}

# Scenario: Memory exhausted
recover_memory_exhausted() {
    log_warn "场景: 内存耗尽"
    
    # Step 1: Check memory usage
    log_info "步骤 1: 检查内存使用"
    run_cmd "free -h" "查看内存概况"
    run_cmd "cat /proc/meminfo | grep -E 'Mem|Swap'" "查看内存详情"
    
    # Show top memory consumers
    log_info "内存使用排名:"
    run_cmd "ps aux --sort=-%mem | head -15" "查看内存使用进程"
    
    # Step 2: Check for memory leaks in Gateway
    log_info "步骤 2: 检查 Gateway 内存使用"
    local container_name="opc200-${OPC_ID,,}-gateway"
    run_cmd "docker stats $container_name --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'" "查看容器内存" 1 0 || true
    
    # Step 3: Restart Gateway
    log_info "步骤 3: 重启 Gateway 释放内存"
    run_cmd "docker restart $container_name" "重启 Gateway" 2 2
    
    # Step 4: Clear system cache
    log_info "步骤 4: 清理系统缓存"
    run_cmd "sync" "同步缓存"
    if [[ -w /proc/sys/vm/drop_caches ]]; then
        run_cmd "echo 3 > /proc/sys/vm/drop_caches" "清理页面缓存" 1 0 || log_warn "无法清理缓存 (权限不足)"
    fi
    
    # Step 5: Verify
    sleep 5
    local mem_info=$(free | grep Mem)
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_usage=$((mem_used * 100 / mem_total))
    
    log_info "当前内存使用: ${mem_usage}%"
    
    if [[ $mem_usage -lt 90 ]]; then
        log_success "内存使用已降低 (当前: ${mem_usage}%)"
        notify_customer "内存已释放，当前使用 ${mem_usage}%" "info"
    else
        log_warn "内存仍然紧张 (${mem_usage}%)，建议增加内存或检查内存泄漏"
        notify_customer "内存清理后仍紧张 (${mem_usage}%)，建议增加内存" "warning"
        return 1
    fi
}

# Scenario: Service unavailable
recover_service_unavailable() {
    log_warn "场景: 服务不可用"
    
    local endpoint
    if [[ ${OPC_ID#OPC-} -le 150 ]]; then
        endpoint="http://opc-${OPC_ID#OPC-}.tailnet.opc200.local"
    else
        endpoint="https://${OPC_ID}.opc200.coidea.ai"
    fi
    
    # Step 1: Check connectivity
    log_info "步骤 1: 检查服务连通性"
    run_cmd "curl -s -o /dev/null -w '%{http_code}' --max-time 10 ${endpoint}/health" "检查健康端点" 3 2 || true
    
    # Step 2: Check DNS
    log_info "步骤 2: 检查 DNS 解析"
    run_cmd "nslookup $(echo $endpoint | sed 's|https\?://||')" "DNS 查询" 1 0 || true
    
    # Step 3: Check Gateway
    log_info "步骤 3: 检查 Gateway 状态"
    recover_gateway_failure
}

# Log audit trail
log_audit() {
    local action="$1"
    local result="$2"
    
    local audit_dir="customers/on-premise/${OPC_ID}/remote-sessions"
    mkdir -p "$audit_dir"
    
    local audit_file="${audit_dir}/emergency-recovery-$(date +%Y%m%d-%H%M%S).log"
    
    cat > "$audit_file" << EOF
---
timestamp: $(date -Iseconds)
operator: $(whoami)
hostname: $(hostname)
action: ${action}
scenario: ${SCENARIO}
dry_run: ${OPC_DRY_RUN:-false}
result: ${result}
command_line: $0 $@
EOF

    log_debug "审计日志已记录: $audit_file"
}

# Main function
main() {
    log_info "OPC200 Emergency Recovery"
    log_info "========================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "场景: $SCENARIO"
    log_info "模式: $([[ "${OPC_DRY_RUN:-false}" == "true" ]] && echo "模拟运行" || echo "实际执行")"
    
    echo ""
    
    # Execute scenario recovery
    local result=0
    case "$SCENARIO" in
        gateway-failure)
            recover_gateway_failure
            result=$?
            ;;
        data-vault-corruption)
            recover_data_vault_corruption
            result=$?
            ;;
        tailscale-disconnect)
            recover_tailscale_disconnect
            result=$?
            ;;
        disk-full)
            recover_disk_full
            result=$?
            ;;
        memory-exhausted)
            recover_memory_exhausted
            result=$?
            ;;
        service-unavailable)
            recover_service_unavailable
            result=$?
            ;;
        *)
            log_error "未知场景: $SCENARIO"
            exit 1
            ;;
    esac
    
    # Log audit
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
