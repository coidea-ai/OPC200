#!/bin/bash
#===============================================================================
# OPC200 Customer Initialization Script
# 用途: 新客户接入时的初始化脚本
# 执行位置: 支持中心 / 客户本地
#===============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
DEFAULT_OPC_ID=""
DEFAULT_MODE="on-premise"  # on-premise | cloud
DEFAULT_DOMAIN="opc200.co"

# 显示帮助
show_help() {
    cat << EOF
OPC200 Customer Initialization Script

Usage: $0 [OPTIONS]

OPTIONS:
    -i, --id ID          客户ID (如: OPC-001)
    -m, --mode MODE      部署模式: on-premise | cloud (默认: on-premise)
    -d, --domain DOMAIN  域名后缀 (默认: opc200.co)
    -f, --feishu TOKEN   飞书 Bot Token
    -t, --tailscale KEY  Tailscale Auth Key (本地模式必需)
    -h, --help          显示此帮助

示例:
    # 初始化本地客户
    $0 -i OPC-001 -m on-premise -t tskey-auth-xxxx

    # 初始化云端客户
    $0 -i OPC-151 -m cloud -f feishu-bot-token

EOF
}

# 解析参数
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
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -f|--feishu)
                FEISHU_TOKEN="$2"
                shift 2
                ;;
            -t|--tailscale)
                TAILSCALE_KEY="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 设置默认值
    MODE=${MODE:-$DEFAULT_MODE}
    DOMAIN=${DOMAIN:-$DEFAULT_DOMAIN}

    # 验证必需参数
    if [[ -z "${OPC_ID:-}" ]]; then
        log_error "缺少客户ID (-i, --id)"
        show_help
        exit 1
    fi

    # 验证 ID 格式
    if ! [[ "$OPC_ID" =~ ^OPC-[0-9]{3}$ ]]; then
        log_error "客户ID格式错误，应为 OPC-XXX (如 OPC-001)"
        exit 1
    fi
}

# 创建客户目录结构
create_customer_structure() {
    log_info "创建客户目录结构: $OPC_ID"
    
    local base_dir="customers/${MODE}/${OPC_ID}"
    
    # 创建目录
    mkdir -p "${base_dir}"/{
        deployment,
        data-vault/{encrypted,local-only,audit-trail/{access-logs,sync-logs,emergency-access}},
        tailscale,
        remote-sessions,
        sync-status,
        compliance/audit-reports
    }
    
    # 复制模板文件
    if [[ "$MODE" == "on-premise" ]]; then
        cp -r customers/_template/on-premise/deployment/* "${base_dir}/deployment/"
    else
        cp -r customers/_template/cloud-hosted/* "${base_dir}/"
    fi
    
    log_success "目录结构创建完成"
}

# 生成配置文件
generate_configs() {
    log_info "生成配置文件"
    
    local base_dir="customers/${MODE}/${OPC_ID}"
    local opc_num=${OPC_ID#OPC-}
    
    # Gateway 配置
    cat > "${base_dir}/deployment/gateway.yml" << EOF
# OPC200 Gateway Configuration
# 客户: ${OPC_ID}
# 模式: ${MODE}
# 生成时间: $(date -Iseconds)

customer:
  id: ${OPC_ID}
  name: "Customer ${opc_num}"
  mode: ${MODE}
  
gateway:
  id: gateway-${OPC_ID,,}
  domain: ${OPC_ID,,}.${DOMAIN}
  
channels:
  feishu:
    enabled: true
    bot_token: ${FEISHU_TOKEN:-""}
    
telemetry:
  enabled: true
  endpoint: https://monitor.${DOMAIN}/api/v1/metrics
  anonymize: true
EOF

    # 数据驻留声明
    cat > "${base_dir}/compliance/data-residency.yml" << EOF
# 数据驻留声明
customer_id: ${OPC_ID}
declaration_date: $(date -Iseconds)

residency:
  primary_location: "${MODE}"
  data_classification: applied
  encryption_at_rest: required
  encryption_in_transit: required
  
tier_1_critical:
  storage: local-only
  backup: encrypted-local
  sync_to_cloud: false
  
tier_2_sensitive:
  storage: local-only
  sync_to_cloud: anonymized-only
  
tier_3_shareable:
  storage: shared
  sync_to_cloud: allowed

emergency_access:
  allowed: true
  requires_authorization: true
  audit_level: comprehensive
  max_duration: 4h
EOF

    log_success "配置文件生成完成"
}

# 设置 Tailscale (本地模式)
setup_tailscale() {
    if [[ "$MODE" != "on-premise" ]]; then
        return 0
    fi
    
    log_info "配置 Tailscale VPN"
    
    if [[ -z "${TAILSCALE_KEY:-}" ]]; then
        log_error "本地模式需要提供 Tailscale Auth Key (-t)"
        exit 1
    fi
    
    local base_dir="customers/${MODE}/${OPC_ID}"
    
    # 保存 Tailscale 配置
    cat > "${base_dir}/tailscale/node-info.yml" << EOF
# Tailscale Node Configuration
node:
  id: ${OPC_ID,,}
  name: opc200-${OPC_ID,,}
  tags:
    - opc
    - ${MODE}
    
auth:
  key: ${TAILSCALE_KEY}
  ephemeral: false
  
network:
  advertise_routes: []
  accept_dns: true
  accept_routes: false
  
emergency_access:
  enabled: true
  acl_tags:
    - support
EOF

    # 保存 auth key
    echo "$TAILSCALE_KEY" > "${base_dir}/tailscale/auth-key"
    chmod 600 "${base_dir}/tailscale/auth-key"
    
    log_success "Tailscale 配置完成"
}

# 注册到主索引
register_customer() {
    log_info "注册到主索引"
    
    local registry="customers/registry/master-index.yml"
    local opc_num=${OPC_ID#OPC-}
    
    # 创建条目
    cat >> "$registry" << EOF

${OPC_ID}:
  id: ${OPC_ID}
  number: ${opc_num}
  mode: ${MODE}
  status: initialized
  created_at: $(date -Iseconds)
  domain: ${OPC_ID,,}.${DOMAIN}
  paths:
    base: customers/${MODE}/${OPC_ID}
    deployment: customers/${MODE}/${OPC_ID}/deployment
    data_vault: customers/${MODE}/${OPC_ID}/data-vault
    tailscale: customers/${MODE}/${OPC_ID}/tailscale
  access:
    emergency_enabled: true
    last_access: null
EOF

    log_success "客户已注册到主索引"
}

# 发送欢迎通知
send_welcome() {
    log_info "准备发送欢迎通知"
    
    # 生成 onboarding 指南路径
    local guide_url="https://docs.${DOMAIN}/onboarding/${MODE}"
    
    log_info "客户 onboarding 指南: ${guide_url}"
    log_info "下一步: 部署 Gateway 并配置飞书 Bot"
}

# 主函数
main() {
    log_info "OPC200 Customer Initialization"
    log_info "=============================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "部署模式: $MODE"
    log_info "域名: ${OPC_ID,,}.${DOMAIN}"
    
    create_customer_structure
    generate_configs
    setup_tailscale
    register_customer
    send_welcome
    
    log_success "=============================="
    log_success "客户 $OPC_ID 初始化完成!"
    log_success "=============================="
    
    echo ""
    echo "后续步骤:"
    echo "  1. 检查配置: cat customers/${MODE}/${OPC_ID}/deployment/gateway.yml"
    echo "  2. 部署 Gateway: ./scripts/deploy/deploy-${MODE}.sh -i ${OPC_ID}"
    echo "  3. 安装 Skills: ./scripts/deploy/install-skills.sh -i ${OPC_ID}"
    echo "  4. 健康检查: ./scripts/maintenance/health-check.sh -i ${OPC_ID}"
}

main "$@"
