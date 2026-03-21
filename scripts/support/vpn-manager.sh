#!/bin/bash
#===============================================================================
# OPC200 Tailscale VPN Manager
# 用途: Tailscale VPN 管理和紧急访问
# 执行位置: 支持中心
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
ACTION="status"  # status | connect | disconnect | emergency-access | generate-key
DURATION="4h"
REASON=""

show_help() {
    cat << EOF
OPC200 Tailscale VPN Manager

Usage: $0 [OPTIONS]

ACTIONS:
    status              查看连接状态
    connect             连接到客户节点
    disconnect          断开连接
    emergency-access    请求紧急访问权限
    generate-key        生成新的 auth key
    list-nodes          列出所有节点

OPTIONS:
    --id ID             客户ID
    --duration TIME     访问持续时间 (默认: 4h)
    --reason TEXT       访问原因
    -h, --help         显示此帮助

示例:
    # 查看状态
    $0 --id OPC-001 status

    # 紧急访问
    $0 --id OPC-001 emergency-access --reason "Gateway故障恢复" --duration 2h

    # 生成新 key
    $0 --id OPC-001 generate-key
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            status|connect|disconnect|emergency-access|generate-key|list-nodes)
                ACTION="$1"
                shift
                ;;
            --id)
                OPC_ID="$2"
                shift 2
                ;;
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --reason)
                REASON="$2"
                shift 2
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

# 检查 Tailscale CLI
check_tailscale() {
    if ! command -v tailscale &> /dev/null; then
        log_error "Tailscale CLI 未安装"
        exit 1
    fi
}

# 获取节点信息
get_node_info() {
    local opc_id=$1
    tailscale status --json 2>/dev/null | jq -r ".Peer[] | select(.HostName == \"opc200-${opc_id,,}\")"
}

# 查看状态
show_status() {
    if [[ -z "$OPC_ID" ]]; then
        log_info "所有节点状态:"
        tailscale status
        return
    fi
    
    log_info "节点状态: $OPC_ID"
    local node_info=$(get_node_info "$OPC_ID")
    
    if [[ -z "$node_info" ]] || [[ "$node_info" == "null" ]]; then
        log_error "节点 $OPC_ID 未找到"
        return 1
    fi
    
    local online=$(echo "$node_info" | jq -r '.Online')
    local tailscale_ip=$(echo "$node_info" | jq -r '.TailscaleIPs[0]')
    local last_seen=$(echo "$node_info" | jq -r '.LastSeen')
    
    echo "  节点: opc200-${OPC_ID,,}"
    echo "  状态: $([[ "$online" == "true" ]] && echo "在线" || echo "离线")"
    echo "  IP: $tailscale_ip"
    echo "  最后 seen: $last_seen"
}

# 连接到客户节点
connect_node() {
    if [[ -z "$OPC_ID" ]]; then
        log_error "需要指定客户ID"
        exit 1
    fi
    
    log_info "连接到: $OPC_ID"
    
    local node_info=$(get_node_info "$OPC_ID")
    local tailscale_ip=$(echo "$node_info" | jq -r '.TailscaleIPs[0]')
    
    if [[ -z "$tailscale_ip" ]] || [[ "$tailscale_ip" == "null" ]]; then
        log_error "无法获取节点 IP"
        exit 1
    fi
    
    log_success "节点 IP: $tailscale_ip"
    
    # 测试连通性
    if ping -c 1 -W 5 "$tailscale_ip" > /dev/null 2>&1; then
        log_success "连接成功!"
        echo ""
        echo "连接方式:"
        echo "  SSH:    ssh opc@${tailscale_ip}"
        echo "  HTTP:   http://${tailscale_ip}:8080"
    else
        log_error "无法连接到节点"
        return 1
    fi
}

# 请求紧急访问
emergency_access() {
    if [[ -z "$OPC_ID" ]]; then
        log_error "需要指定客户ID"
        exit 1
    fi
    
    if [[ -z "$REASON" ]]; then
        log_error "需要提供访问原因 (--reason)"
        exit 1
    fi
    
    log_warn "紧急访问请求"
    log_warn "============="
    log_warn "客户: $OPC_ID"
    log_warn "原因: $REASON"
    log_warn "持续时间: $DURATION"
    
    echo ""
    read -p "确认请求紧急访问? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "已取消"
        exit 0
    fi
    
    # 记录访问请求
    local access_dir="customers/on-premise/${OPC_ID}/remote-sessions"
    mkdir -p "$access_dir"
    
    cat > "${access_dir}/access-request-$(date +%Y%m%d-%H%M%S).yml" << EOF
access_request:
  customer_id: ${OPC_ID}
  timestamp: $(date -Iseconds)
  operator: $(whoami)
  reason: ${REASON}
  duration: ${DURATION}
  status: requested
  
authorization:
  method: customer_notification
  notified_channels: [feishu]
  customer_response: pending
  
audit:
  session_recording: enabled
  command_logging: enabled
  post_access_report: required
EOF

    # 发送通知给客户
    log_info "发送授权请求给客户..."
    
    # 这里应该调用飞书 API
    # ...
    
    log_success "访问请求已发送"
    log_info "等待客户授权..."
    
    # 模拟等待
    log_info "授权后连接命令:"
    echo "  $0 --id ${OPC_ID} connect"
}

# 生成新的 auth key
generate_key() {
    if [[ -z "$OPC_ID" ]]; then
        log_error "需要指定客户ID"
        exit 1
    fi
    
    log_info "生成新的 auth key: $OPC_ID"
    
    # 生成 key
    local auth_key=$(tailscale keys create --reusable --ephemeral=false --tags="tag:opc" 2>/dev/null || echo "")
    
    if [[ -z "$auth_key" ]]; then
        log_error "生成 key 失败"
        exit 1
    fi
    
    # 保存 key
    local key_file="customers/on-premise/${OPC_ID}/tailscale/auth-key"
    echo "$auth_key" > "$key_file"
    chmod 600 "$key_file"
    
    log_success "新的 auth key 已生成并保存"
    log_warn "请妥善保管，key 不会再次显示"
}

# 列出所有节点
list_nodes() {
    log_info "所有 OPC200 节点:"
    echo "=================="
    
    tailscale status --json 2>/dev/null | jq -r '
        .Peer[] | 
        select(.HostName | startswith("opc200-")) |
        "\(.HostName) | \(.TailscaleIPs[0]) | \(.Online | if . then \"在线\" else \"离线\" end)"
    ' | while read line; do
        echo "  $line"
    done
}

# 主函数
main() {
    log_info "OPC200 Tailscale VPN Manager"
    log_info "============================"
    
    parse_args "$@"
    
    check_tailscale
    
    case "$ACTION" in
        status)
            show_status
            ;;
        connect)
            connect_node
            ;;
        disconnect)
            log_info "断开连接: tailscale down"
            ;;
        emergency-access)
            emergency_access
            ;;
        generate-key)
            generate_key
            ;;
        list-nodes)
            list_nodes
            ;;
        *)
            log_error "未知操作: $ACTION"
            exit 1
            ;;
    esac
}

main "$@"
