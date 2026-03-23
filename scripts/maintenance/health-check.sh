#!/bin/bash
#===============================================================================
# OPC200 Health Check Script
# 用途: 系统和客户健康检查
# 执行位置: 支持中心 / 客户服务器
#===============================================================================

set -uo pipefail

# 脚本信息
SCRIPT_NAME="$(basename "$0")"
SCRIPT_VERSION="2.2.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查执行权限
check_execution_permission() {
    if [[ "$EUID" -ne 0 ]]; then
        echo "警告: 脚本未以 root 权限运行，某些检查可能受限" && 2
    fi
}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 默认配置
OPC_ID=""
MODE="all"  # all | on-premise | cloud
VERBOSE=false
OUTPUT_JSON=false
GENERATE_DOCS=false

show_help() {
    cat << EOF
OPC200 Health Check Script v${SCRIPT_VERSION}

Usage: $0 [OPTIONS]

OPTIONS:
    -i, --id ID          客户ID (如: OPC-001)
    -m, --mode MODE      检查模式: all | on-premise | cloud
    -v, --verbose        详细输出
    -j, --json           JSON 格式输出
    -d, --generate-docs  生成文档
    -h, --help          显示此帮助

示例:
    # 检查单个客户
    $0 -i OPC-001

    # 检查所有客户
    $0 -m all

    # JSON 输出
    $0 -i OPC-001 -j
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--id)
                OPC_ID="$2"
                shift 2
                ;;
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -j|--json)
                OUTPUT_JSON=true
                shift
                ;;
            -d|--generate-docs)
                GENERATE_DOCS=true
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
}

# 生成文档
generate_documentation() {
    cat << 'EOF'
# Health Check Documentation

## Overview
The health check script performs comprehensive system and service validation.

## Checks Performed

### System Resources
- CPU usage monitoring
- Memory usage monitoring
- Disk space monitoring

### Services
- Docker daemon status
- Gateway container health
- Tailscale VPN connectivity

### Data Integrity
- Skills installation verification
- Data vault encryption status
- Backup currency check

## Exit Codes
- 0: All checks passed
- 1: Warnings detected
- 2: Critical issues found

## JSON Output Format
```json
{
  "timestamp": "2024-03-24T10:00:00Z",
  "customer_id": "OPC-001",
  "overall_status": "healthy",
  "checks": [
    {
      "name": "CPU",
      "status": "OK",
      "message": "使用率: 45%"
    }
  ]
}
```
EOF
}

# 初始化检查结果
declare -A CHECK_RESULTS
declare -a CHECK_ORDER

add_check() {
    local name=$1
    local status=$2
    local message=$3
    
    CHECK_RESULTS["$name"]="${status}|${message}"
    CHECK_ORDER+=("$name")
}

# JSON 输出函数
output_json() {
    local customer_id=${OPC_ID:-"unknown"}
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Determine overall status
    local overall_status="healthy"
    for name in "${CHECK_ORDER[@]}"; do
        local result="${CHECK_RESULTS[$name]}"
        local status
        status=$(echo "$result" | cut -d'|' -f1)
        if [[ "$status" == "CRITICAL" ]]; then
            overall_status="critical"
            break
        elif [[ "$status" == "WARNING" && "$overall_status" != "critical" ]]; then
            overall_status="warning"
        fi
    done
    
    # Build JSON output
    echo "{"
    echo "  \"timestamp\": \"$timestamp\","
    echo "  \"customer_id\": \"$customer_id\","
    echo "  \"overall_status\": \"$overall_status\","
    echo "  \"script_version\": \"$SCRIPT_VERSION\","
    echo "  \"checks\": ["
    
    local first=true
    for name in "${CHECK_ORDER[@]}"; do
        local result="${CHECK_RESULTS[$name]}"
        local status
        status=$(echo "$result" | cut -d'|' -f1)
        local message
        message=$(echo "$result" | cut -d'|' -f2)
        
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        
        # Escape message for JSON
        local escaped_message
        escaped_message=$(echo "$message" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
        
        echo -n "    {"
        echo -n "\"name\": \"$name\", "
        echo -n "\"status\": \"$status\", "
        echo -n "\"message\": \"$escaped_message\""
        echo -n "}"
    done
    
    echo ""
    echo "  ]"
    echo "}"
}

# 检查系统资源
check_system_resources() {
    local issues=0
    
    # CPU
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    # Use awk for comparison instead of bc
    if awk "BEGIN {exit !($cpu_usage > 80)}"; then
        add_check "CPU" "WARNING" "使用率: ${cpu_usage}% (高)"
        ((issues++))
    else
        add_check "CPU" "OK" "使用率: ${cpu_usage}%"
    fi
    
    # 内存
    local mem_info
    mem_info=$(free | grep Mem)
    local mem_total
    mem_total=$(echo "$mem_info" | awk '{print $2}')
    local mem_used
    mem_used=$(echo "$mem_info" | awk '{print $3}')
    local mem_usage=$((mem_used * 100 / mem_total))
    
    if [[ $mem_usage -gt 85 ]]; then
        add_check "Memory" "WARNING" "使用率: ${mem_usage}% (高)"
        ((issues++))
    else
        add_check "Memory" "OK" "使用率: ${mem_usage}%"
    fi
    
    # 磁盘
    local disk_usage
    disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    if [[ $disk_usage -gt 85 ]]; then
        add_check "Disk" "WARNING" "使用率: ${disk_usage}% (高)"
        ((issues++))
    else
        add_check "Disk" "OK" "使用率: ${disk_usage}%"
    fi
    
    return $issues
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        add_check "Docker" "CRITICAL" "未安装"
        return 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        add_check "Docker" "CRITICAL" "服务未运行"
        return 1
    fi
    
    add_check "Docker" "OK" "运行正常"
    return 0
}

# 检查 Gateway
check_gateway() {
    local opc_id=$1
    local container="opc200-${opc_id,,}-gateway"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        add_check "Gateway" "CRITICAL" "容器未运行"
        return 1
    fi
    
    # 检查健康状态
    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
    
    if [[ "$health" == "healthy" ]]; then
        add_check "Gateway" "OK" "健康状态良好"
    elif [[ "$health" == "unhealthy" ]]; then
        add_check "Gateway" "WARNING" "健康检查失败"
        return 1
    else
        add_check "Gateway" "WARNING" "健康状态未知"
    fi
    
    # 检查端口
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        add_check "Gateway-API" "OK" "API 响应正常"
    else
        add_check "Gateway-API" "WARNING" "API 无响应"
        return 1
    fi
    
    return 0
}

# 检查 Tailscale
check_tailscale() {
    if ! command -v tailscale &> /dev/null; then
        add_check "Tailscale" "WARNING" "未安装"
        return 1
    fi
    
    if ! tailscale status &> /dev/null; then
        add_check "Tailscale" "WARNING" "未连接"
        return 1
    fi
    
    local tailscale_ip
    tailscale_ip=$(tailscale ip -4 2>/dev/null || echo "unknown")
    add_check "Tailscale" "OK" "已连接 (${tailscale_ip})"
    return 0
}

# 检查 Skills
check_skills() {
    local opc_id=$1
    local skills_dir="/opt/opc200/${opc_id}/skills"
    
    if [[ ! -d "$skills_dir" ]]; then
        add_check "Skills" "WARNING" "目录不存在"
        return 1
    fi
    
    local skill_count
    skill_count=$(find "$skills_dir" -maxdepth 1 -type d | wc -l)
    skill_count=$((skill_count - 1))
    
    if [[ $skill_count -eq 0 ]]; then
        add_check "Skills" "WARNING" "未安装 Skills"
        return 1
    fi
    
    add_check "Skills" "OK" "已安装 ${skill_count} 个 Skills"
    return 0
}

# 检查数据保险箱
check_data_vault() {
    local opc_id=$1
    local vault_dir="/opt/opc200/${opc_id}/data-vault"
    
    if [[ ! -d "$vault_dir" ]]; then
        add_check "DataVault" "WARNING" "数据保险箱不存在"
        return 1
    fi
    
    # 检查加密状态
    if [[ -d "${vault_dir}/encrypted" ]]; then
        add_check "DataVault-Encryption" "OK" "加密存储已启用"
    else
        add_check "DataVault-Encryption" "WARNING" "未启用加密"
    fi
    
    # 检查本地存储
    if [[ -d "${vault_dir}/local-only" ]]; then
        add_check "DataVault-Local" "OK" "本地存储已配置"
    fi
    
    return 0
}

# 检查日志
check_logs() {
    local opc_id=$1
    local logs_dir="/opt/opc200/${opc_id}/logs"
    
    if [[ ! -d "$logs_dir" ]]; then
        add_check "Logs" "WARNING" "日志目录不存在"
        return 1
    fi
    
    # 检查日志大小
    local log_size
    log_size=$(du -sm "$logs_dir" | cut -f1)
    if [[ $log_size -gt 1000 ]]; then
        add_check "Logs" "WARNING" "日志过大: ${log_size}MB (建议清理)"
    else
        add_check "Logs" "OK" "日志大小: ${log_size}MB"
    fi
    
    # 检查最近错误
    local recent_errors
    recent_errors=$(find "$logs_dir" -name "*.log" -mtime -1 -exec grep -i "error" {} + 2>/dev/null | wc -l)
    if [[ $recent_errors -gt 10 ]]; then
        add_check "Log-Errors" "WARNING" "最近24小时有 ${recent_errors} 条错误"
    else
        add_check "Log-Errors" "OK" "最近24小时错误数: ${recent_errors}"
    fi
    
    return 0
}

# 检查备份
check_backup() {
    local opc_id=$1
    local backup_dir="/opt/opc200/${opc_id}/backup"
    
    if [[ ! -d "$backup_dir" ]]; then
        add_check "Backup" "WARNING" "备份目录不存在"
        return 1
    fi
    
    # 检查最近备份
    local latest_backup
    latest_backup=$(find "$backup_dir" -type f -mtime -1 | head -1)
    if [[ -n "$latest_backup" ]]; then
        add_check "Backup" "OK" "最近备份: $(basename "$latest_backup")"
    else
        add_check "Backup" "WARNING" "24小时内无备份"
    fi
    
    return 0
}

# 检查单个客户
check_customer() {
    local opc_id=$1
    local mode=$2
    
    log_info "检查客户: $opc_id ($mode)"
    echo "================================"
    
    CHECK_RESULTS=()
    CHECK_ORDER=()
    
    local total_issues=0
    
    # 通用检查
    check_system_resources
    ((total_issues+=$?))
    
    check_docker
    ((total_issues+=$?))
    
    if [[ "$mode" == "on-premise" ]]; then
        # 本地部署特有检查
        check_gateway "$opc_id"
        ((total_issues+=$?))
        
        check_tailscale
        ((total_issues+=$?))
        
        check_skills "$opc_id"
        ((total_issues+=$?))
        
        check_data_vault "$opc_id"
        
        check_logs "$opc_id"
        
        check_backup "$opc_id"
    fi
    
    # 输出结果
    echo ""
    echo "检查结果:"
    echo "---------"
    
    for name in "${CHECK_ORDER[@]}"; do
        local result="${CHECK_RESULTS[$name]}"
        local status
        status=$(echo "$result" | cut -d'|' -f1)
        local message
        message=$(echo "$result" | cut -d'|' -f2)
        
        case "$status" in
            OK)
                log_success "$name: $message"
                ;;
            WARNING)
                log_warn "$name: $message"
                ;;
            CRITICAL)
                log_error "$name: $message"
                ;;
        esac
    done
    
    echo ""
    if [[ $total_issues -eq 0 ]]; then
        log_success "总体状态: 健康"
        return 0
    elif [[ $total_issues -lt 3 ]]; then
        log_warn "总体状态: 警告 (${total_issues} 个问题)"
        return 1
    else
        log_error "总体状态: 严重 (${total_issues} 个问题)"
        return 2
    fi
}

# 检查所有客户
check_all_customers() {
    log_info "检查所有客户"
    echo "================"
    
    local summary_file="/tmp/health-check-summary-$(date +%Y%m%d-%H%M%S).txt"
    
    # 本地客户
    for customer_dir in customers/on-premise/OPC-*; do
        if [[ -d "$customer_dir" ]]; then
            local opc_id
            opc_id=$(basename "$customer_dir")
            
            # SSH 到客户服务器检查（简化版）
            echo "$opc_id: on-premise" >> "$summary_file"
        fi
    done
    
    # 云端客户
    for customer_dir in customers/cloud-hosted/OPC-*; do
        if [[ -d "$customer_dir" ]]; then
            local opc_id
            opc_id=$(basename "$customer_dir")
            echo "$opc_id: cloud-hosted" >> "$summary_file"
        fi
    done
    
    log_info "摘要已保存: $summary_file"
}

# 主函数
main() {
    check_execution_permission
    parse_args "$@"
    
    # 生成文档模式
    if [[ "$GENERATE_DOCS" == "true" ]]; then
        generate_documentation
        exit 0
    fi
    
    if [[ -n "$OPC_ID" ]]; then
        # 确定客户模式
        if [[ -d "customers/on-premise/${OPC_ID}" ]]; then
            check_customer "$OPC_ID" "on-premise"
        elif [[ -d "customers/cloud-hosted/${OPC_ID}" ]]; then
            check_customer "$OPC_ID" "cloud-hosted"
        else
            log_error "客户 $OPC_ID 不存在"
            exit 1
        fi
    else
        check_all_customers
    fi
    
    # JSON 输出模式
    if [[ "$OUTPUT_JSON" == "true" ]]; then
        output_json
    fi
}

main "$@"
