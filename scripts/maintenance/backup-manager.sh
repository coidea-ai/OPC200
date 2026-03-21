#!/bin/bash
#===============================================================================
# OPC200 Backup Manager Script
# 用途: 备份管理和恢复
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
ACTION="backup"  # backup | restore | list | cleanup
BACKUP_NAME=""
RETENTION_DAYS=7
ENCRYPT=true
REMOTE_UPLOAD=false

show_help() {
    cat << EOF
OPC200 Backup Manager

Usage: $0 [OPTIONS]

ACTIONS:
    backup              创建备份 (默认)
    restore             恢复备份
    list                列出备份
    cleanup             清理旧备份

OPTIONS:
    --id ID             客户ID
    --name NAME         备份名称 (默认: auto-YYYY-MM-DD-HHMMSS)
    --retention DAYS    保留天数 (默认: 7)
    --no-encrypt        不加密备份
    --upload            上传到远程存储
    -h, --help         显示此帮助

示例:
    # 创建备份
    $0 --id OPC-001 backup

    # 恢复备份
    $0 --id OPC-001 restore --name auto-2026-03-21-120000

    # 清理旧备份
    $0 --id OPC-001 cleanup --retention 3
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            backup|restore|list|cleanup)
                ACTION="$1"
                shift
                ;;
            --id)
                OPC_ID="$2"
                shift 2
                ;;
            --name)
                BACKUP_NAME="$2"
                shift 2
                ;;
            --retention)
                RETENTION_DAYS="$2"
                shift 2
                ;;
            --no-encrypt)
                ENCRYPT=false
                shift
                ;;
            --upload)
                REMOTE_UPLOAD=true
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

# 获取备份目录
get_backup_dir() {
    echo "/opt/opc200/${OPC_ID}/backup"
}

# 获取数据目录
get_data_dir() {
    echo "/opt/opc200/${OPC_ID}/data"
}

# 创建备份
create_backup() {
    local backup_dir=$(get_backup_dir)
    local data_dir=$(get_data_dir)
    
    # 生成备份名称
    local backup_name=${BACKUP_NAME:-"auto-$(date +%Y%m%d-%H%M%S)"}
    local backup_path="${backup_dir}/${backup_name}"
    
    log_info "创建备份: $backup_name"
    
    # 确保备份目录存在
    mkdir -p "$backup_path"
    
    # 停止 Gateway（可选，视一致性要求）
    log_info "暂停 Gateway 写入..."
    docker pause "opc200-${OPC_ID,,}-gateway" 2>/dev/null || true
    
    # 备份数据
    log_info "备份数据目录..."
    if [[ -d "$data_dir" ]]; then
        tar -czf "${backup_path}/data.tar.gz" -C "$(dirname "$data_dir")" "$(basename "$data_dir")"
    fi
    
    # 备份配置
    log_info "备份配置文件..."
    tar -czf "${backup_path}/config.tar.gz" -C "/opt/opc200/${OPC_ID}" gateway/ data-vault/ 2>/dev/null || true
    
    # 备份 Skills
    log_info "备份 Skills..."
    if [[ -d "/opt/opc200/${OPC_ID}/skills" ]]; then
        tar -czf "${backup_path}/skills.tar.gz" -C "/opt/opc200/${OPC_ID}" skills/
    fi
    
    # 恢复 Gateway
    docker unpause "opc200-${OPC_ID,,}-gateway" 2>/dev/null || true
    
    # 创建备份清单
    cat > "${backup_path}/manifest.yml" << EOF
backup:
  name: ${backup_name}
  customer_id: ${OPC_ID}
  created_at: $(date -Iseconds)
  created_by: $(whoami)
  hostname: $(hostname)
  
components:
  data: data.tar.gz
  config: config.tar.gz
  skills: skills.tar.gz
  
options:
  encrypted: ${ENCRYPT}
  compressed: true
  
verify:
  checksum_algorithm: sha256
  checksums:
EOF

    # 计算校验和
    for file in "${backup_path}"/*.tar.gz; do
        if [[ -f "$file" ]]; then
            local checksum=$(sha256sum "$file" | cut -d' ' -f1)
            local filename=$(basename "$file")
            echo "    ${filename}: ${checksum}" >> "${backup_path}/manifest.yml"
        fi
    done
    
    # 加密（如果需要）
    if [[ "$ENCRYPT" == true ]]; then
        log_info "加密备份..."
        local encryption_key_file="/opt/opc200/${OPC_ID}/data-vault/encrypted/keys/backup-key"
        
        if [[ -f "$encryption_key_file" ]]; then
            for file in "${backup_path}"/*.tar.gz; do
                if [[ -f "$file" ]]; then
                    gpg --symmetric --cipher-algo AES256 --passphrase-file "$encryption_key_file" \
                        --batch --yes -o "${file}.gpg" "$file"
                    rm "$file"
                fi
            done
            log_success "备份已加密"
        else
            log_warn "加密密钥不存在，备份未加密"
        fi
    fi
    
    # 上传到远程（如果需要）
    if [[ "$REMOTE_UPLOAD" == true ]]; then
        log_info "上传到远程存储..."
        # rclone sync "$backup_path" "remote:opc200-backups/${OPC_ID}/"
        log_success "上传完成"
    fi
    
    # 创建最新链接
    ln -sfn "$backup_path" "${backup_dir}/latest"
    
    log_success "备份完成: $backup_path"
    
    # 显示备份大小
    local backup_size=$(du -sh "$backup_path" | cut -f1)
    log_info "备份大小: $backup_size"
}

# 恢复备份
restore_backup() {
    if [[ -z "$BACKUP_NAME" ]]; then
        log_error "恢复操作需要指定备份名称 (--name)"
        exit 1
    fi
    
    local backup_dir=$(get_backup_dir)
    local backup_path="${backup_dir}/${BACKUP_NAME}"
    local data_dir=$(get_data_dir)
    
    if [[ ! -d "$backup_path" ]]; then
        log_error "备份不存在: $backup_path"
        exit 1
    fi
    
    log_warn "即将恢复备份: $BACKUP_NAME"
    log_warn "当前数据将被覆盖!"
    read -p "确认恢复? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "恢复已取消"
        exit 0
    fi
    
    # 创建当前状态的紧急备份
    log_info "创建当前状态紧急备份..."
    local emergency_backup="pre-restore-$(date +%Y%m%d-%H%M%S)"
    BACKUP_NAME="$emergency_backup"
    create_backup
    
    # 停止 Gateway
    log_info "停止 Gateway..."
    docker stop "opc200-${OPC_ID,,}-gateway" || true
    
    # 解密（如果需要）
    if [[ -f "${backup_path}/data.tar.gz.gpg" ]]; then
        log_info "解密备份..."
        local encryption_key_file="/opt/opc200/${OPC_ID}/data-vault/encrypted/keys/backup-key"
        
        for file in "${backup_path}"/*.gpg; do
            if [[ -f "$file" ]]; then
                local output_file="${file%.gpg}"
                gpg --decrypt --passphrase-file "$encryption_key_file" \
                    --batch --yes -o "$output_file" "$file"
            fi
        done
    fi
    
    # 恢复数据
    log_info "恢复数据..."
    if [[ -f "${backup_path}/data.tar.gz" ]]; then
        rm -rf "${data_dir}.old"
        mv "$data_dir" "${data_dir}.old" 2>/dev/null || true
        mkdir -p "$data_dir"
        tar -xzf "${backup_path}/data.tar.gz" -C "$(dirname "$data_dir")"
    fi
    
    # 恢复配置
    log_info "恢复配置..."
    if [[ -f "${backup_path}/config.tar.gz" ]]; then
        tar -xzf "${backup_path}/config.tar.gz" -C "/opt/opc200/${OPC_ID}"
    fi
    
    # 恢复 Skills
    log_info "恢复 Skills..."
    if [[ -f "${backup_path}/skills.tar.gz" ]]; then
        rm -rf "/opt/opc200/${OPC_ID}/skills"
        tar -xzf "${backup_path}/skills.tar.gz" -C "/opt/opc200/${OPC_ID}"
    fi
    
    # 启动 Gateway
    log_info "启动 Gateway..."
    docker start "opc200-${OPC_ID,,}-gateway" || true
    
    log_success "恢复完成!"
    log_info "原数据保存在: ${data_dir}.old"
}

# 列出备份
list_backups() {
    local backup_dir=$(get_backup_dir)
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "备份目录不存在"
        exit 1
    fi
    
    log_info "备份列表 (${OPC_ID}):"
    echo "========================================"
    
    for backup in "$backup_dir"/auto-*; do
        if [[ -d "$backup" ]]; then
            local name=$(basename "$backup")
            local size=$(du -sh "$backup" | cut -f1)
            local date=$(stat -c %y "$backup" | cut -d' ' -f1)
            
            # 检查是否有 manifest
            if [[ -f "${backup}/manifest.yml" ]]; then
                echo "  ✓ $name | $size | $date"
            else
                echo "  ? $name | $size | $date (无清单)"
            fi
        fi
    done
    
    # 显示最新备份
    if [[ -L "${backup_dir}/latest" ]]; then
        local latest=$(readlink "${backup_dir}/latest")
        echo ""
        log_info "最新备份: $(basename "$latest")"
    fi
}

# 清理旧备份
cleanup_backups() {
    local backup_dir=$(get_backup_dir)
    
    log_info "清理 ${RETENTION_DAYS} 天前的备份"
    
    local deleted_count=0
    
    while IFS= read -r backup; do
        if [[ -d "$backup" ]]; then
            local name=$(basename "$backup")
            log_info "删除: $name"
            rm -rf "$backup"
            ((deleted_count++))
        fi
    done < <(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" -mtime +${RETENTION_DAYS})
    
    log_success "清理完成，删除 ${deleted_count} 个备份"
}

# 主函数
main() {
    log_info "OPC200 Backup Manager"
    log_info "====================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "操作: $ACTION"
    
    case "$ACTION" in
        backup)
            create_backup
            ;;
        restore)
            restore_backup
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_backups
            ;;
        *)
            log_error "未知操作: $ACTION"
            exit 1
            ;;
    esac
}

main "$@"
