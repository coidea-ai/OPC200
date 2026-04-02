#!/bin/bash
#===============================================================================
# OPC200 Backup Manager Script
# 用途: 备份管理和恢复
# 执行位置: 支持中心 / 客户服务器
#===============================================================================

set -euo pipefail

# Source common logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"

# Check required commands
check_dependencies() {
    local deps=("tar" "sha256sum" "date")
    
    if [[ "$ENCRYPT" == true ]]; then
        deps+=("gpg")
    fi
    
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
}

# Default configuration
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
    --upload            上传到远程存储 (需要配置 rclone)
    --dry-run           模拟运行，不实际执行
    -v, --verbose       启用调试日志
    -h, --help          显示此帮助

依赖检查:
    - tar, sha256sum, date (必需)
    - gpg (加密时需要)
    - rclone (远程上传时需要)

示例:
    # 创建备份
    $0 --id OPC-001 backup

    # 模拟创建备份 (不实际执行)
    $0 --id OPC-001 --dry-run backup

    # 恢复备份
    $0 --id OPC-001 restore --name auto-2026-03-21-120000

    # 清理旧备份
    $0 --id OPC-001 cleanup --retention 3

    # 详细输出模式
    $0 --id OPC-001 -v backup
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
            --dry-run)
                export OPC_DRY_RUN="true"
                log_warn "Dry run mode enabled - no changes will be made"
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

    if [[ -z "$OPC_ID" ]]; then
        log_error "缺少客户ID (--id)"
        exit 1
    fi
}

# Get backup directory
get_backup_dir() {
    echo "/opt/opc200/${OPC_ID}/backup"
}

# Get data directory
get_data_dir() {
    echo "/opt/opc200/${OPC_ID}/data"
}

# Progress callback for tar
tar_with_progress() {
    local output_file="$1"
    shift
    local source_dir="$1"
    local source_base=$(basename "$source_dir")
    local source_parent=$(dirname "$source_dir")
    
    log_info "正在打包: $source_base"
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] 将创建: $output_file"
        return 0
    fi
    
    # Use tar with verbose output and count files for progress
    local total_files=$(find "$source_dir" -type f 2>/dev/null | wc -l)
    log_info "文件总数: $total_files"
    
    # Create tar.gz with progress
    tar -czf "$output_file" -C "$source_parent" "$source_base" 2>&1 &
    local tar_pid=$!
    
    # Show progress
    local last_size=0
    while kill -0 $tar_pid 2>/dev/null; do
        if [[ -f "$output_file" ]]; then
            local current_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
            if [[ $current_size -gt $last_size ]]; then
                log_debug "已打包: $(numfmt --to=iec $current_size 2>/dev/null || echo "${current_size} bytes")"
                last_size=$current_size
            fi
        fi
        sleep 1
    done
    
    wait $tar_pid
    log_success "打包完成: $output_file"
}

# Create backup
create_backup() {
    local backup_dir=$(get_backup_dir)
    local data_dir=$(get_data_dir)
    
    # Generate backup name
    local backup_name=${BACKUP_NAME:-"auto-$(date +%Y%m%d-%H%M%S)"}
    local backup_path="${backup_dir}/${backup_name}"
    
    log_info "创建备份: $backup_name"
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] 备份目录: $backup_path"
        log_warn "[DRY-RUN] 数据目录: $data_dir"
        log_warn "[DRY-RUN] 将创建: data.tar.gz, config.tar.gz, skills.tar.gz"
        log_success "模拟备份完成"
        return 0
    fi
    
    # Ensure backup directory exists
    mkdir -p "$backup_path"
    
    # Create temporary status file for tracking
    local status_file="${backup_path}/.backup_status"
    echo "IN_PROGRESS" > "$status_file"
    
    # Pause Gateway (optional, depending on consistency requirements)
    log_info "暂停 Gateway 写入..."
    local container_name="opc200-${OPC_ID,,}-gateway"
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        docker pause "$container_name" 2>/dev/null || log_warn "无法暂停 Gateway，继续备份..."
    else
        log_warn "Gateway 容器未运行，跳过暂停步骤"
    fi
    
    # Backup data with progress
    log_info "备份数据目录..."
    if [[ -d "$data_dir" ]]; then
        tar_with_progress "${backup_path}/data.tar.gz" "$data_dir"
    else
        log_warn "数据目录不存在: $data_dir"
    fi
    
    # Backup config
    log_info "备份配置文件..."
    local config_dir="/opt/opc200/${OPC_ID}"
    if [[ -d "$config_dir/gateway" ]] || [[ -d "$config_dir/data-vault" ]]; then
        tar -czf "${backup_path}/config.tar.gz" -C "$config_dir" gateway/ data-vault/ 2>/dev/null || log_warn "配置备份部分失败"
    fi
    
    # Backup Skills
    log_info "备份 Skills..."
    if [[ -d "$config_dir/skills" ]]; then
        tar_with_progress "${backup_path}/skills.tar.gz" "$config_dir/skills"
    else
        log_warn "Skills 目录不存在"
    fi
    
    # Resume Gateway
    log_info "恢复 Gateway..."
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        docker unpause "$container_name" 2>/dev/null || log_warn "无法恢复 Gateway"
    fi
    
    # Create manifest
    log_info "创建备份清单..."
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

    # Calculate checksums
    for file in "${backup_path}"/*.tar.gz; do
        if [[ -f "$file" ]]; then
            local checksum=$(sha256sum "$file" | cut -d' ' -f1)
            local filename=$(basename "$file")
            echo "    ${filename}: ${checksum}" >> "${backup_path}/manifest.yml"
        fi
    done
    
    # Encrypt if needed
    if [[ "$ENCRYPT" == true ]]; then
        log_info "加密备份..."
        local encryption_key_file="/opt/opc200/${OPC_ID}/data-vault/encrypted/keys/backup-key"
        
        if [[ -f "$encryption_key_file" ]]; then
            for file in "${backup_path}"/*.tar.gz; do
                if [[ -f "$file" ]]; then
                    log_debug "加密: $file"
                    gpg --symmetric --cipher-algo AES256 --passphrase-file "$encryption_key_file" \
                        --batch --yes -o "${file}.gpg" "$file"
                    rm "$file"
                fi
            done
            log_success "备份已加密"
        else
            log_warn "加密密钥不存在: $encryption_key_file"
            log_warn "备份未加密"
        fi
    fi
    
    # Upload to remote if needed
    if [[ "$REMOTE_UPLOAD" == true ]]; then
        log_info "上传到远程存储..."
        if command -v rclone >/dev/null 2>&1; then
            # Check if rclone remote is configured
            if rclone listremotes | grep -q "^remote:"; then
                rclone sync "$backup_path" "remote:opc200-backups/${OPC_ID}/" --progress
                log_success "上传完成"
            else
                log_error "rclone remote 'remote:' 未配置"
                log_info "请运行: rclone config"
            fi
        else
            log_error "rclone 未安装，无法上传"
            log_info "安装: https://rclone.org/install/"
        fi
    fi
    
    # Create latest symlink
    ln -sfn "$backup_path" "${backup_dir}/latest"
    
    # Mark backup as complete
    echo "COMPLETED" > "$status_file"
    
    log_success "备份完成: $backup_path"
    
    # Show backup size
    local backup_size=$(du -sh "$backup_path" | cut -f1)
    log_info "备份大小: $backup_size"
}

# Restore backup
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
    
    # Verify backup status
    local status_file="${backup_path}/.backup_status"
    if [[ -f "$status_file" ]]; then
        local status=$(cat "$status_file")
        if [[ "$status" != "COMPLETED" ]]; then
            log_warn "备份状态为: $status"
            read -p "确认要继续恢复吗? (yes/no): " confirm
            [[ "$confirm" != "yes" ]] && { log_info "恢复已取消"; exit 0; }
        fi
    fi
    
    log_warn "即将恢复备份: $BACKUP_NAME"
    log_warn "当前数据将被覆盖!"
    read -p "确认恢复? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "恢复已取消"
        exit 0
    fi
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] 将恢复备份: $backup_path"
        return 0
    fi
    
    # Create emergency backup of current state
    log_info "创建当前状态紧急备份..."
    local emergency_backup="pre-restore-$(date +%Y%m%d-%H%M%S)"
    BACKUP_NAME="$emergency_backup"
    create_backup
    
    # Stop Gateway
    log_info "停止 Gateway..."
    local container_name="opc200-${OPC_ID,,}-gateway"
    docker stop "$container_name" 2>/dev/null || log_warn "Gateway 已停止或不存在"
    
    # Decrypt if needed
    if [[ -f "${backup_path}/data.tar.gz.gpg" ]]; then
        log_info "解密备份..."
        local encryption_key_file="/opt/opc200/${OPC_ID}/data-vault/encrypted/keys/backup-key"
        
        if [[ ! -f "$encryption_key_file" ]]; then
            log_error "解密密钥不存在: $encryption_key_file"
            exit 1
        fi
        
        for file in "${backup_path}"/*.gpg; do
            if [[ -f "$file" ]]; then
                local output_file="${file%.gpg}"
                log_debug "解密: $file"
                gpg --decrypt --passphrase-file "$encryption_key_file" \
                    --batch --yes -o "$output_file" "$file"
            fi
        done
    fi
    
    # Restore data
    log_info "恢复数据..."
    if [[ -f "${backup_path}/data.tar.gz" ]]; then
        rm -rf "${data_dir}.old"
        mv "$data_dir" "${data_dir}.old" 2>/dev/null || true
        mkdir -p "$data_dir"
        tar -xzf "${backup_path}/data.tar.gz" -C "$(dirname "$data_dir")"
        log_success "数据已恢复"
    else
        log_warn "数据备份文件不存在"
    fi
    
    # Restore config
    log_info "恢复配置..."
    if [[ -f "${backup_path}/config.tar.gz" ]]; then
        tar -xzf "${backup_path}/config.tar.gz" -C "/opt/opc200/${OPC_ID}"
        log_success "配置已恢复"
    fi
    
    # Restore Skills
    log_info "恢复 Skills..."
    if [[ -f "${backup_path}/skills.tar.gz" ]]; then
        rm -rf "/opt/opc200/${OPC_ID}/skills"
        tar -xzf "${backup_path}/skills.tar.gz" -C "/opt/opc200/${OPC_ID}"
        log_success "Skills 已恢复"
    fi
    
    # Start Gateway
    log_info "启动 Gateway..."
    docker start "$container_name" 2>/dev/null || log_warn "Gateway 启动失败，可能需要手动启动"
    
    log_success "恢复完成!"
    log_info "原数据保存在: ${data_dir}.old"
}

# List backups
list_backups() {
    local backup_dir=$(get_backup_dir)
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi
    
    log_info "备份列表 (${OPC_ID}):"
    echo "========================================"
    printf "%-25s %-10s %-12s %-10s\n" "名称" "大小" "日期" "状态"
    echo "----------------------------------------"
    
    for backup in "$backup_dir"/auto-*; do
        if [[ -d "$backup" ]]; then
            local name=$(basename "$backup")
            local size=$(du -sh "$backup" | cut -f1)
            local date=$(stat -c %y "$backup" | cut -d' ' -f1)
            local status="?"
            
            # Check backup status
            if [[ -f "${backup}/.backup_status" ]]; then
                status=$(cat "${backup}/.backup_status")
                case "$status" in
                    COMPLETED) status="✓" ;;
                    IN_PROGRESS) status="⟳" ;;
                    FAILED) status="✗" ;;
                    *) status="?" ;;
                esac
            fi
            
            # Check if manifest exists
            if [[ -f "${backup}/manifest.yml" ]]; then
                printf "%-25s %-10s %-12s %-10s\n" "$name" "$size" "$date" "$status"
            else
                printf "%-25s %-10s %-12s %-10s\n" "$name" "$size" "$date" "(无清单)"
            fi
        fi
    done
    
    # Show latest backup
    if [[ -L "${backup_dir}/latest" ]]; then
        local latest=$(readlink "${backup_dir}/latest")
        echo ""
        log_info "最新备份: $(basename "$latest")"
    fi
}

# Cleanup old backups
cleanup_backups() {
    local backup_dir=$(get_backup_dir)
    
    log_info "清理 ${RETENTION_DAYS} 天前的备份"
    
    local deleted_count=0
    local total_freed=0
    
    while IFS= read -r backup; do
        if [[ -d "$backup" ]]; then
            local name=$(basename "$backup")
            local size=$(du -sb "$backup" | cut -f1)
            
            log_info "删除: $name ($(du -sh "$backup" | cut -f1))"
            
            if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
                log_warn "[DRY-RUN] 将删除: $backup"
            else
                rm -rf "$backup"
                ((deleted_count++))
                total_freed=$((total_freed + size))
            fi
        fi
    done <<< "$(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" -mtime +${RETENTION_DAYS} 2>/dev/null)"
    
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_warn "[DRY-RUN] 模拟清理完成"
    else
        log_success "清理完成，删除 ${deleted_count} 个备份，释放 $(numfmt --to=iec $total_freed 2>/dev/null || echo "${total_freed} bytes")"
    fi
}

# Main function
main() {
    log_info "OPC200 Backup Manager"
    log_info "====================="
    
    parse_args "$@"
    check_dependencies
    
    log_info "客户ID: $OPC_ID"
    log_info "操作: $ACTION"
    [[ "$ENCRYPT" == true ]] && log_info "加密: 启用"
    [[ "$REMOTE_UPLOAD" == true ]] && log_info "远程上传: 启用"
    
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
