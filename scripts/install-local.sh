#!/bin/bash
# OPC200 本地部署脚本
# 版本: 2026.1

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
OPC200_VERSION="2026.1"
INSTALL_DIR="/home/opc200"
CONFIG_DIR="$INSTALL_DIR/.openclaw/opc200"

# 打印函数
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 检查 root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "请不要使用 root 用户运行此脚本"
        print_info "脚本会自动创建 opc200 用户"
        exit 1
    fi
}

# 检查系统要求
check_requirements() {
    print_info "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        print_error "不支持的操作系统"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        print_warning "仅在 Ubuntu/Debian 上测试过，其他系统可能有问题"
    fi
    
    # 检查内存
    MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $MEM_GB -lt 4 ]]; then
        print_warning "内存不足 4GB，可能影响性能"
    fi
    
    # 检查磁盘
    DISK_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $DISK_GB -lt 20 ]]; then
        print_warning "磁盘空间不足 20GB"
    fi
    
    print_success "系统检查完成"
}

# 安装依赖
install_dependencies() {
    print_info "安装依赖..."
    
    sudo apt-get update
    sudo apt-get install -y \
        curl \
        git \
        sqlite3 \
        jq \
        openssl \
        net-tools
    
    # 安装 Node.js 18+
    if ! command -v node &> /dev/null || [[ $(node -v | cut -d'v' -f2 | cut -d'.' -f1) -lt 18 ]]; then
        print_info "安装 Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    print_success "依赖安装完成"
}

# 创建用户
create_user() {
    print_info "创建 opc200 用户..."
    
    if ! id "opc200" &> /dev/null; then
        sudo useradd -r -m -s /bin/bash opc200
        sudo usermod -aG sudo opc200
        print_success "用户 opc200 创建成功"
    else
        print_warning "用户 opc200 已存在"
    fi
}

# 安装 OpenClaw
install_openclaw() {
    print_info "安装 OpenClaw..."
    
    # 切换到 opc200 用户执行
    sudo su - opc200 -c "
        if ! command -v openclaw &> /dev/null; then
            curl -fsSL https://openclaw.ai/install.sh | bash
        fi
    "
    
    print_success "OpenClaw 安装完成"
}

# 安装 Tailscale
install_tailscale() {
    print_info "安装 Tailscale..."
    
    if ! command -v tailscale &> /dev/null; then
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
    
    print_success "Tailscale 安装完成"
}

# 创建目录结构
create_directories() {
    print_info "创建目录结构..."
    
    sudo su - opc200 -c "
        mkdir -p $CONFIG_DIR/{configs,security,logs,memory,skills}
        mkdir -p $CONFIG_DIR/security-reports
    "
    
    print_success "目录结构创建完成"
}

# 下载配置文件
download_configs() {
    print_info "下载配置文件..."
    
    # 生成随机 token
    GATEWAY_TOKEN=$(openssl rand -base64 32)
    
    sudo su - opc200 -c "
        # 下载 gateway 配置
        curl -fsSL https://raw.githubusercontent.com/coidea/opc200/main/configs/gateway-secure.yml \
            -o $CONFIG_DIR/configs/gateway-secure.yml
        
        # 设置环境变量
        echo 'export OPC200_GATEWAY_TOKEN=$GATEWAY_TOKEN' >> ~/.bashrc
        echo 'export OPC200_TENANT_ID=OPC-001' >> ~/.bashrc
    "
    
    print_success "配置文件下载完成"
    print_info "Gateway Token: $GATEWAY_TOKEN"
    print_warning "请保存此 Token，之后无法查看"
}

# 安装 Skills
install_skills() {
    print_info "安装核心 Skills..."
    
    sudo su - opc200 -c "
        source ~/.bashrc
        
        # 等待 OpenClaw 就绪
        sleep 2
        
        # 安装 Skills
        clawhub install TheSethRose/clawdbot-security-check || true
        clawhub install xiaowenzhou/active-maintenance || true
        clawhub install arminnaimi/agent-team-orchestration || true
        clawhub install dennis-da-menace/agent-memory || true
        clawhub install coidea/opc-journal || true
    "
    
    print_success "Skills 安装完成"
}

# 配置 systemd
setup_systemd() {
    print_info "配置 systemd 服务..."
    
    sudo tee /etc/systemd/system/opc200-gateway.service > /dev/null <> EOF
[Unit]
Description=OPC200 OpenClaw Gateway
After=network.target

[Service]
Type=simple
User=opc200
Group=opc200
Environment="HOME=/home/opc200"
Environment="NODE_ENV=production"
EnvironmentFile=/home/opc200/.openclaw/opc200/.env
ExecStart=/home/opc200/.openclaw/bin/openclaw gateway start --config /home/opc200/.openclaw/opc200/configs/gateway-secure.yml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable opc200-gateway
    
    print_success "systemd 配置完成"
}

# 设置权限
set_permissions() {
    print_info "设置权限..."
    
    sudo chown -R opc200:opc200 /home/opc200
    sudo chmod 700 /home/opc200/.openclaw
    sudo chmod 600 /home/opc200/.openclaw/opc200/configs/*.yml 2>/dev/null || true
    
    print_success "权限设置完成"
}

# 配置夜间审计
setup_audit() {
    print_info "配置夜间安全审计..."
    
    sudo su - opc200 -c "
        curl -fsSL https://raw.githubusercontent.com/coidea/opc200/main/scripts/nightly-security-audit.sh \
            -o $CONFIG_DIR/scripts/nightly-security-audit.sh
        chmod +x $CONFIG_DIR/scripts/nightly-security-audit.sh
    "
    
    # 添加 cron 任务
    (sudo crontab -u opc200 -l 2>/dev/null || echo "") | \
        grep -v "nightly-security-audit" | \
        { cat; echo "0 2 * * * /home/opc200/.openclaw/opc200/scripts/nightly-security-audit.sh"; } | \
        sudo crontab -u opc200 -
    
    print_success "夜间审计配置完成"
}

# 显示完成信息
show_completion() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}       OPC200 本地部署完成！${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 后续步骤:"
    echo ""
    echo "1. 配置 Tailscale (获取 auth key 从支持中心):"
    echo "   sudo tailscale up --authkey tskey-auth-xxx"
    echo ""
    echo "2. 启动 Gateway:"
    echo "   sudo systemctl start opc200-gateway"
    echo ""
    echo "3. 查看状态:"
    echo "   sudo systemctl status opc200-gateway"
    echo "   tail -f /home/opc200/.openclaw/opc200/logs/gateway.log"
    echo ""
    echo "4. 注册到支持中心:"
    echo "   opc200 register --customer-id OPC-001"
    echo ""
    echo "📖 文档: https://docs.opc200.co"
    echo "🆘 支持: support@opc200.co"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 主函数
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "       OPC200 本地部署脚本 v2026.1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    check_requirements
    install_dependencies
    create_user
    install_openclaw
    install_tailscale
    create_directories
    download_configs
    install_skills
    setup_systemd
    set_permissions
    setup_audit
    show_completion
}

# 运行主函数
main "$@"
