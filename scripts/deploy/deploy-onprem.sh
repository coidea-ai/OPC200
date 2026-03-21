#!/bin/bash
#===============================================================================
# OPC200 On-Premise Deployment Script
# 用途: 本地客户 Gateway 部署
# 执行位置: 客户服务器
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
SKIP_TAILSCALE=false
SKIP_VERIFY=false

show_help() {
    cat << EOF
OPC200 On-Premise Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -i, --id ID          客户ID (如: OPC-001)
    --skip-tailscale     跳过 Tailscale 安装
    --skip-verify        跳过部署验证
    -h, --help          显示此帮助

示例:
    $0 -i OPC-001
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--id)
                OPC_ID="$2"
                shift 2
                ;;
            --skip-tailscale)
                SKIP_TAILSCALE=true
                shift
                ;;
            --skip-verify)
                SKIP_VERIFY=true
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

    if [[ -z "$OPC_ID" ]]; then
        log_error "缺少客户ID (-i, --id)"
        exit 1
    fi
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求"
    
    # 检查 root
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 权限运行"
        exit 1
    fi
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_info "安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_info "安装 Docker Compose..."
        apt-get update && apt-get install -y docker-compose-plugin
    fi
    
    # 检查资源
    local cpu_cores=$(nproc)
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    local disk_gb=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
    
    log_info "CPU: ${cpu_cores} cores, 内存: ${mem_gb}GB, 磁盘: ${disk_gb}GB"
    
    if [[ $cpu_cores -lt 2 ]]; then
        log_warn "建议至少 2 CPU cores"
    fi
    if [[ $mem_gb -lt 4 ]]; then
        log_warn "建议至少 4GB 内存"
    fi
    
    log_success "系统检查通过"
}

# 安装 Tailscale
install_tailscale() {
    if [[ "$SKIP_TAILSCALE" == true ]]; then
        log_info "跳过 Tailscale 安装"
        return 0
    fi
    
    log_info "安装 Tailscale"
    
    # 安装
    curl -fsSL https://tailscale.com/install.sh | sh
    
    # 读取 auth key
    local auth_key_file="/opt/opc200/${OPC_ID}/tailscale/auth-key"
    if [[ ! -f "$auth_key_file" ]]; then
        log_error "Tailscale auth key 不存在: $auth_key_file"
        exit 1
    fi
    
    local auth_key=$(cat "$auth_key_file")
    
    # 启动并连接
    tailscale up --authkey="$auth_key" --hostname="opc200-${OPC_ID,,}" --accept-dns=true
    
    # 等待连接
    log_info "等待 Tailscale 连接..."
    sleep 5
    
    if tailscale status &> /dev/null; then
        log_success "Tailscale 连接成功"
        local tailscale_ip=$(tailscale ip -4)
        log_info "Tailscale IP: $tailscale_ip"
    else
        log_error "Tailscale 连接失败"
        exit 1
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构"
    
    local dirs=(
        "/opt/opc200/${OPC_ID}/gateway"
        "/opt/opc200/${OPC_ID}/data"
        "/opt/opc200/${OPC_ID}/logs"
        "/opt/opc200/${OPC_ID}/skills"
        "/opt/opc200/${OPC_ID}/backup"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
    done
    
    # 设置权限
    chmod 700 "/opt/opc200/${OPC_ID}/data"
    chmod 700 "/opt/opc200/${OPC_ID}/backup"
    
    log_success "目录结构创建完成"
}

# 部署 Gateway
deploy_gateway() {
    log_info "部署 OpenClaw Gateway"
    
    local compose_file="/opt/opc200/${OPC_ID}/gateway/docker-compose.yml"
    
    # 生成 docker-compose
    cat > "$compose_file" << EOF
version: '3.8'

services:
  gateway:
    image: openclaw/gateway:latest
    container_name: opc200-${OPC_ID,,}-gateway
    restart: unless-stopped
    
    ports:
      - "127.0.0.1:8080:8080"  # 本地访问
      
    volumes:
      - /opt/opc200/${OPC_ID}/data:/data
      - /opt/opc200/${OPC_ID}/logs:/logs
      - /opt/opc200/${OPC_ID}/skills:/skills
      - /opt/opc200/${OPC_ID}/gateway/config.yml:/config.yml:ro
      
    environment:
      - OPC_ID=${OPC_ID}
      - NODE_ENV=production
      - DATA_DIR=/data
      - LOG_LEVEL=info
      
    networks:
      - opc200-network
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 本地监控代理
  monitoring-agent:
    image: openclaw/monitoring-agent:latest
    container_name: opc200-${OPC_ID,,}-monitor
    restart: unless-stopped
    
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/opc200/${OPC_ID}/logs:/logs:ro
      
    environment:
      - OPC_ID=${OPC_ID}
      - COLLECTOR_ENDPOINT=https://monitor.opc200.co/api/v1/metrics
      
    networks:
      - opc200-network

networks:
  opc200-network:
    driver: bridge
EOF

    # 复制配置文件
    local config_src="customers/on-premise/${OPC_ID}/deployment/gateway.yml"
    if [[ -f "$config_src" ]]; then
        cp "$config_src" "/opt/opc200/${OPC_ID}/gateway/config.yml"
    fi
    
    # 启动
    cd "/opt/opc200/${OPC_ID}/gateway"
    docker-compose up -d
    
    # 等待启动
    log_info "等待 Gateway 启动..."
    sleep 10
    
    log_success "Gateway 部署完成"
}

# 验证部署
verify_deployment() {
    if [[ "$SKIP_VERIFY" == true ]]; then
        return 0
    fi
    
    log_info "验证部署"
    
    # 检查容器状态
    local containers=("opc200-${OPC_ID,,}-gateway" "opc200-${OPC_ID,,}-monitor")
    
    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            log_success "容器 $container 运行正常"
        else
            log_error "容器 $container 未运行"
            docker logs "$container" 2>/dev/null || true
            exit 1
        fi
    done
    
    # 检查 Gateway 健康
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Gateway 健康检查通过"
    else
        log_warn "Gateway 健康检查未通过，请检查日志"
    fi
    
    # 检查 Tailscale
    if tailscale status &> /dev/null; then
        log_success "Tailscale 连接正常"
    else
        log_warn "Tailscale 连接异常"
    fi
    
    log_success "部署验证完成"
}

# 设置系统服务
setup_systemd() {
    log_info "设置系统服务"
    
    cat > "/etc/systemd/system/opc200-${OPC_ID,,}.service" << EOF
[Unit]
Description=OPC200 Gateway for ${OPC_ID}
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/opc200/${OPC_ID}/gateway
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "opc200-${OPC_ID,,}.service"
    
    log_success "系统服务设置完成"
}

# 保存部署信息
save_deployment_info() {
    log_info "保存部署信息"
    
    cat > "/opt/opc200/${OPC_ID}/deployment-info.yml" << EOF
# OPC200 Deployment Information
customer_id: ${OPC_ID}
deployment_mode: on-premise
deployed_at: $(date -Iseconds)
server_info:
  hostname: $(hostname)
  ip: $(hostname -I | awk '{print $1}')
  tailscale_ip: $(tailscale ip -4 2>/dev/null || echo "N/A")
components:
  gateway:
    version: $(docker inspect openclaw/gateway:latest --format='{{.Id}}' 2>/dev/null | cut -c1-12 || echo "unknown")
    status: running
  tailscale:
    version: $(tailscale version 2>/dev/null | head -1 || echo "unknown")
    status: $(tailscale status 2>/dev/null && echo "connected" || echo "disconnected")
directories:
  gateway: /opt/opc200/${OPC_ID}/gateway
  data: /opt/opc200/${OPC_ID}/data
  logs: /opt/opc200/${OPC_ID}/logs
  skills: /opt/opc200/${OPC_ID}/skills
backup:
  schedule: daily at 02:00
  retention: 7 days
EOF

    log_success "部署信息已保存"
}

# 主函数
main() {
    log_info "OPC200 On-Premise Deployment"
    log_info "============================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "模式: on-premise"
    
    check_requirements
    create_directories
    install_tailscale
    deploy_gateway
    setup_systemd
    verify_deployment
    save_deployment_info
    
    log_success "============================="
    log_success "部署完成!"
    log_success "============================="
    
    echo ""
    echo "部署信息:"
    echo "  客户ID: $OPC_ID"
    echo "  Gateway: http://localhost:8080"
    echo "  日志: /opt/opc200/${OPC_ID}/logs/"
    echo "  数据: /opt/opc200/${OPC_ID}/data/"
    echo ""
    echo "常用命令:"
    echo "  查看状态: docker ps"
    echo "  查看日志: docker logs opc200-${OPC_ID,,}-gateway"
    echo "  重启服务: systemctl restart opc200-${OPC_ID,,}"
    echo ""
    echo "下一步:"
    echo "  1. 安装 Skills: ./scripts/deploy/install-skills.sh -i ${OPC_ID}"
    echo "  2. 配置飞书 Bot"
    echo "  3. 运行健康检查"
}

main "$@"
