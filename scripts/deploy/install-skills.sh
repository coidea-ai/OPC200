#!/bin/bash
#===============================================================================
# OPC200 Skills Installation Script
# 用途: 为客户安装/更新/卸载 Skills
# 执行位置: 支持中心 / 客户服务器
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
ACTION="install"  # install | update | uninstall | list
SKILL=""
VERSION="latest"
SKIP_DEPS=false

show_help() {
    cat << EOF
OPC200 Skills Installation Script

Usage: $0 [OPTIONS]

ACTIONS:
    -i, --install        安装 Skills (默认)
    -u, --update         更新 Skills
    -r, --uninstall      卸载 Skills
    -l, --list           列出已安装 Skills

OPTIONS:
    --id ID              客户ID (如: OPC-001)
    --skill SKILL        Skill 名称 (如: opc-journal-core)
    --version VERSION    版本号 (默认: latest)
    --skip-deps          跳过依赖安装
    -h, --help          显示此帮助

示例:
    # 安装单个 Skill
    $0 --id OPC-001 --skill opc-journal-core

    # 更新所有 Skills
    $0 --id OPC-001 --update

    # 安装完整套件
    $0 --id OPC-001 --skill opc-journal-suite

    # 列出已安装 Skills
    $0 --id OPC-001 --list
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--install)
                ACTION="install"
                shift
                ;;
            -u|--update)
                ACTION="update"
                shift
                ;;
            -r|--uninstall)
                ACTION="uninstall"
                shift
                ;;
            -l|--list)
                ACTION="list"
                shift
                ;;
            --id)
                OPC_ID="$2"
                shift 2
                ;;
            --skill)
                SKILL="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --skip-deps)
                SKIP_DEPS=true
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
        log_error "缺少客户ID (--id)"
        exit 1
    fi
}

# 获取部署模式
get_deployment_mode() {
    if [[ -d "customers/on-premise/${OPC_ID}" ]]; then
        echo "on-premise"
    elif [[ -d "customers/cloud-hosted/${OPC_ID}" ]]; then
        echo "cloud-hosted"
    else
        log_error "客户 ${OPC_ID} 不存在"
        exit 1
    fi
}

# 获取 Skills 目录
get_skills_dir() {
    local mode=$1
    if [[ "$mode" == "on-premise" ]]; then
        echo "/opt/opc200/${OPC_ID}/skills"
    else
        echo "customers/cloud-hosted/${OPC_ID}/skills"
    fi
}

# 检查 clawhub
check_clawhub() {
    if ! command -v clawhub &> /dev/null; then
        log_error "clawhub 未安装"
        log_info "安装命令: npm install -g @openclaw/clawhub"
        exit 1
    fi
}

# 安装单个 Skill
install_single_skill() {
    local skill=$1
    local version=$2
    local skills_dir=$3
    
    log_info "安装 Skill: ${skill}:${version}"
    
    # 检查本地缓存
    local cache_dir="knowledge-packs/cache/${skill}/${version}"
    if [[ -d "$cache_dir" ]]; then
        log_info "使用本地缓存"
        cp -r "$cache_dir" "${skills_dir}/${skill}"
    else
        # 从 clawhub 安装
        if [[ "$mode" == "on-premise" ]]; then
            # 本地客户：下载后传输
            clawhub download "coidea/${skill}" --version "$version" --output "${cache_dir}.tar.gz"
            mkdir -p "$cache_dir"
            tar -xzf "${cache_dir}.tar.gz" -C "$cache_dir"
            rm "${cache_dir}.tar.gz"
            cp -r "$cache_dir" "${skills_dir}/${skill}"
        else
            # 云端客户：直接安装
            clawhub install "coidea/${skill}" --version "$version" --target "$skills_dir"
        fi
    fi
    
    # 运行安装后脚本
    if [[ -f "${skills_dir}/${skill}/scripts/install.sh" ]]; then
        log_info "运行安装后脚本"
        bash "${skills_dir}/${skill}/scripts/install.sh" --customer-id "$OPC_ID"
    fi
    
    log_success "Skill ${skill} 安装完成"
}

# 安装 OPC Journal Suite
install_journal_suite() {
    local skills_dir=$1
    
    log_info "安装 OPC Journal Suite"
    
    local skills=(
        "opc-journal-core"
        "opc-pattern-recognition"
        "opc-milestone-tracker"
        "opc-async-task-manager"
        "opc-insight-generator"
    )
    
    for skill in "${skills[@]}"; do
        install_single_skill "$skill" "$VERSION" "$skills_dir"
    done
    
    # 安装依赖 Skills
    if [[ "$SKIP_DEPS" != true ]]; then
        log_info "安装依赖 Skills"
        install_single_skill "agent-team-orchestration" "latest" "$skills_dir"
        install_single_skill "active-maintenance" "latest" "$skills_dir"
    fi
    
    log_success "OPC Journal Suite 安装完成"
}

# 列出已安装 Skills
list_skills() {
    local skills_dir=$1
    
    log_info "已安装 Skills (${OPC_ID}):"
    
    if [[ ! -d "$skills_dir" ]]; then
        log_warn "Skills 目录不存在"
        return
    fi
    
    for skill_dir in "$skills_dir"/*/; do
        if [[ -d "$skill_dir" ]]; then
            local skill_name=$(basename "$skill_dir")
            local version="unknown"
            
            if [[ -f "${skill_dir}/SKILL.md" ]]; then
                version=$(grep -E "^version:" "${skill_dir}/SKILL.md" | cut -d: -f2 | tr -d ' ' || echo "unknown")
            fi
            
            echo "  • ${skill_name} (${version})"
        fi
    done
}

# 更新 Skills
update_skills() {
    local skills_dir=$1
    
    log_info "更新所有 Skills"
    
    if [[ ! -d "$skills_dir" ]]; then
        log_error "Skills 目录不存在"
        exit 1
    fi
    
    for skill_dir in "$skills_dir"/*/; do
        if [[ -d "$skill_dir" ]]; then
            local skill_name=$(basename "$skill_dir")
            
            # 备份旧版本
            local backup_dir="${skills_dir}/.backups/${skill_name}-$(date +%Y%m%d-%H%M%S)"
            mkdir -p "$backup_dir"
            cp -r "$skill_dir" "$backup_dir/"
            
            # 更新
            rm -rf "$skill_dir"
            install_single_skill "$skill_name" "latest" "$skills_dir"
            
            log_success "${skill_name} 已更新"
        fi
    done
    
    log_success "所有 Skills 更新完成"
}

# 卸载 Skill
uninstall_skill() {
    local skill=$1
    local skills_dir=$2
    
    log_info "卸载 Skill: ${skill}"
    
    local skill_path="${skills_dir}/${skill}"
    
    if [[ ! -d "$skill_path" ]]; then
        log_warn "Skill ${skill} 未安装"
        return
    fi
    
    # 运行卸载前脚本
    if [[ -f "${skill_path}/scripts/uninstall.sh" ]]; then
        log_info "运行卸载前脚本"
        bash "${skill_path}/scripts/uninstall.sh" --customer-id "$OPC_ID"
    fi
    
    # 备份
    local backup_dir="${skills_dir}/.backups/${skill}-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    mv "$skill_path" "$backup_dir/"
    
    log_success "Skill ${skill} 已卸载 (备份: ${backup_dir})"
}

# 重启 Gateway 以应用变更
restart_gateway() {
    local mode=$1
    
    log_info "重启 Gateway 以应用变更"
    
    if [[ "$mode" == "on-premise" ]]; then
        # 本地：通过 systemd 重启
        if systemctl is-active "opc200-${OPC_ID,,}.service" &> /dev/null; then
            systemctl restart "opc200-${OPC_ID,,}.service"
        else
            cd "/opt/opc200/${OPC_ID}/gateway" && docker-compose restart
        fi
    else
        # 云端：通过 kubectl 或 docker-compose
        log_info "云端 Gateway 重启请联系平台团队"
    fi
    
    log_success "Gateway 重启完成"
}

# 主函数
main() {
    log_info "OPC200 Skills Manager"
    log_info "====================="
    
    parse_args "$@"
    
    local mode=$(get_deployment_mode)
    local skills_dir=$(get_skills_dir "$mode")
    
    log_info "客户ID: $OPC_ID"
    log_info "部署模式: $mode"
    log_info "操作: $ACTION"
    log_info "Skills目录: $skills_dir"
    
    # 确保目录存在
    mkdir -p "$skills_dir"
    
    case "$ACTION" in
        install)
            if [[ -z "$SKILL" ]]; then
                log_error "安装操作需要指定 Skill (--skill)"
                exit 1
            fi
            
            check_clawhub
            
            if [[ "$SKILL" == "opc-journal-suite" ]]; then
                install_journal_suite "$skills_dir"
            else
                install_single_skill "$SKILL" "$VERSION" "$skills_dir"
            fi
            
            restart_gateway "$mode"
            ;;
            
        update)
            check_clawhub
            update_skills "$skills_dir"
            restart_gateway "$mode"
            ;;
            
        uninstall)
            if [[ -z "$SKILL" ]]; then
                log_error "卸载操作需要指定 Skill (--skill)"
                exit 1
            fi
            
            uninstall_skill "$SKILL" "$skills_dir"
            restart_gateway "$mode"
            ;;
            
        list)
            list_skills "$skills_dir"
            ;;
            
        *)
            log_error "未知操作: $ACTION"
            exit 1
            ;;
    esac
    
    log_success "====================="
    log_success "操作完成!"
    log_success "====================="
}

main "$@"
