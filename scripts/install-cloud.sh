#!/bin/bash
# OPC200 云端托管部署脚本
# 版本: 2026.1

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 参数
GATEWAY_URL=""
TOKEN=""
TENANT_ID=""

# 打印函数
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 帮助
show_help() {
    cat <> EOF
OPC200 云端部署脚本

用法:
  curl -fsSL https://opc200.co/install-cloud.sh | bash -s -- [选项]

选项:
  --gateway-url URL    Gateway URL (必需)
  --token TOKEN        认证 Token (必需)
  --tenant-id ID       租户 ID (必需)
  -h, --help           显示帮助

示例:
  bash install-cloud.sh --gateway-url "https://opc-151.opc200.co" \
                        --token "xxx" \
                        --tenant-id "OPC-151"
EOF
}

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --gateway-url)
                GATEWAY_URL="$2"
                shift 2
                ;;
            --token)
                TOKEN="$2"
                shift 2
                ;;
            --tenant-id)
                TENANT_ID="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 验证必需参数
    if [[ -z "$GATEWAY_URL" || -z "$TOKEN" || -z "$TENANT_ID" ]]; then
        print_error "缺少必需参数"
        show_help
        exit 1
    fi
}

# 检查要求
check_requirements() {
    print_info "检查系统要求..."
    
    # 检查 curl
    if ! command -v curl &> /dev/null; then
        print_error "需要 curl"
        exit 1
    fi
    
    print_success "检查通过"
}

# 下载配置
download_config() {
    print_info "下载配置文件..."
    
    mkdir -p ~/.openclaw/opc200/configs
    
    # 下载配置
    curl -fsSL "${GATEWAY_URL}/config/download" \
        -H "Authorization: Bearer ${TOKEN}" \
        -o ~/.openclaw/opc200/configs/cloud.yml \
        || {
            print_error "下载配置失败"
            exit 1
        }
    
    print_success "配置下载完成"
}

# 安装 OpenClaw CLI
install_cli() {
    print_info "安装 OpenClaw CLI..."
    
    if ! command -v openclaw &> /dev/null; then
        curl -fsSL https://openclaw.ai/install.sh | bash
        
        # 添加到 PATH
        export PATH="$HOME/.openclaw/bin:$PATH"
        echo 'export PATH="$HOME/.openclaw/bin:$PATH"' >> ~/.bashrc
    fi
    
    print_success "CLI 安装完成"
}

# 配置环境
setup_environment() {
    print_info "配置环境..."
    
    cat > ~/.openclaw/opc200/.env <> EOF
OPC200_GATEWAY_URL=${GATEWAY_URL}
OPC200_TOKEN=${TOKEN}
OPC200_TENANT_ID=${TENANT_ID}
OPC200_MODE=cloud
EOF
    
    print_success "环境配置完成"
}

# 验证连接
verify_connection() {
    print_info "验证 Gateway 连接..."
    
    openclaw ping --gateway "$GATEWAY_URL" --token "$TOKEN" || {
        print_error "无法连接到 Gateway"
        exit 1
    }
    
    print_success "连接验证成功"
}

# 启动服务
start_service() {
    print_info "启动 OPC200 服务..."
    
    openclaw agent start \
        --gateway "$GATEWAY_URL" \
        --config ~/.openclaw/opc200/configs/cloud.yml \
        --daemon
    
    print_success "服务已启动"
}

# 显示完成信息
show_completion() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}       OPC200 云端部署完成！${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 信息:"
    echo "   租户 ID: $TENANT_ID"
    echo "   Gateway: $GATEWAY_URL"
    echo ""
    echo "🚀 开始使用:"
    echo "   opc200 start           # 启动交互式会话"
    echo "   opc200 status          # 查看状态"
    echo "   opc200 journal         # 打开 Journal"
    echo ""
    echo "📖 文档: https://docs.opc200.co"
    echo "🆘 支持: support@opc200.co"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 主函数
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "       OPC200 云端部署脚本 v2026.1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    parse_args "$@"
    check_requirements
    install_cli
    download_config
    setup_environment
    verify_connection
    start_service
    show_completion
}

# 运行
main "$@"
