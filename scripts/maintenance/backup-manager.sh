#!/bin/bash
#===============================================================================
# OPC200 Backup Manager Script
#===============================================================================

set -euo pipefail

# Source libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"
source "$SCRIPT_DIR/../lib/config.sh"

# Check required commands
check_dependencies() {
    local deps=("tar" "sha256sum" "date")
    [[ "$OPC_BACKUP_ENCRYPT" == "true" ]] && deps+=("gpg")
    [[ "$REMOTE_UPLOAD" == "true" ]] && deps+=("rclone")
    
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
}

# Parse arguments
OPC_ID=""
ACTION="backup"
BACKUP_NAME=""
REMOTE_UPLOAD="false"
CONFIG_FILE=""

show_help() {
    cat << EOF
OPC200 Backup Manager

Usage: $0 --id OPC-XXX [OPTIONS] ACTION

ACTIONS:
    backup    Create backup (default)
    restore   Restore backup
    list      List backups
    cleanup   Cleanup old backups

OPTIONS:
    --id ID           Customer ID (required)
    --name NAME       Backup name (default: auto-YYYY-MM-DD-HHMMSS)
    --retention DAYS  Retention days (default: \$OPC_BACKUP_RETENTION_DAYS)
    --no-encrypt      Disable backup encryption
    --upload          Upload to remote storage
    --config FILE     Use specific config file
    --dry-run         Simulate run without actual execution
    -v, --verbose     Enable debug logging
    -h, --help        Show this help

Examples:
    $0 --id OPC-001 backup
    $0 --id OPC-001 --dry-run backup
    $0 --id OPC-001 restore --name auto-2026-03-21-120000
    $0 --id OPC-001 cleanup
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            backup|restore|list|cleanup)
                ACTION="$1"; shift ;;
            --id) OPC_ID="$2"; shift 2 ;;
            --name) BACKUP_NAME="$2"; shift 2 ;;
            --retention) export OPC_BACKUP_RETENTION_DAYS="$2"; shift 2 ;;
            --no-encrypt) export OPC_BACKUP_ENCRYPT="false"; shift ;;
            --upload) REMOTE_UPLOAD="true"; shift ;;
            --config) CONFIG_FILE="$2"; shift 2 ;;
            --dry-run) export OPC_DRY_RUN="true"; log_warn "Dry run mode enabled"; shift ;;
            -v|--verbose) export OPC_LOG_LEVEL="DEBUG"; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) log_error "Unknown parameter: $1"; exit 1 ;;
        esac
    done

    if [[ -z "$OPC_ID" ]]; then
        log_error "Missing customer ID (--id)"
        exit 1
    fi
    
    if ! opc_validate_customer_id "$OPC_ID"; then
        log_error "Invalid customer ID format: $OPC_ID"
        exit 1
    fi
}

# Get directories using config
dirs=()
get_backup_dir() { echo "${dirs[0]}"; }
get_data_dir() { echo "${dirs[1]}"; }
get_config_dir() { echo "${dirs[2]}"; }

setup_dirs() {
    dirs=(
        "$(opc_get_customer_dir "$OPC_ID" backup)"
        "$(opc_get_customer_dir "$OPC_ID" data)"
        "$(opc_get_customer_dir "$OPC_ID" config)"
    )
}

# Create backup
create_backup() {
    local backup_dir=$(get_backup_dir)
    local data_dir=$(get_data_dir)
    local backup_name=${BACKUP_NAME:-"auto-$(date +%Y%m%d-%H%M%S)"}
    local backup_path="${backup_dir}/${backup_name}"
    
    log_info "Creating backup: $backup_name"
    
    if [[ "$OPC_DRY_RUN" == "true" ]]; then
        log_warn "[DRY-RUN] Backup path: $backup_path"
        log_warn "[DRY-RUN] Data dir: $data_dir"
        log_success "Simulation complete"
        return 0
    fi
    
    mkdir -p "$backup_path"
    echo "IN_PROGRESS" > "${backup_path}/.backup_status"
    
    local container_name="opc200-${OPC_ID,,}-gateway"
    docker pause "$container_name" 2>/dev/null || log_warn "Could not pause Gateway"
    
    # Backup data
    if [[ -d "$data_dir" ]]; then
        log_info "Backing up data..."
        tar -czf "${backup_path}/data.tar.gz" -C "$(dirname "$data_dir")" "$(basename "$data_dir")"
    fi
    
    # Backup config
    local config_parent="$(opc_get_customer_dir "$OPC_ID" base)"
    if [[ -d "$config_parent/gateway" ]] || [[ -d "$config_parent/data-vault" ]]; then
        log_info "Backing up config..."
        tar -czf "${backup_path}/config.tar.gz" -C "$config_parent" gateway/ data-vault/ 2>/dev/null || true
    fi
    
    # Backup skills
    if [[ -d "$config_parent/skills" ]]; then
        log_info "Backing up skills..."
        tar -czf "${backup_path}/skills.tar.gz" -C "$config_parent" skills/
    fi
    
    docker unpause "$container_name" 2>/dev/null || true
    
    # Create manifest
    cat > "${backup_path}/manifest.yml" << EOF
backup:
  name: ${backup_name}
  customer_id: ${OPC_ID}
  created_at: $(date -Iseconds)
  created_by: $(whoami)
  hostname: $(hostname)
  encrypted: ${OPC_BACKUP_ENCRYPT}
  checksums:
EOF

    for file in "${backup_path}"/*.tar.gz; do
        if [[ -f "$file" ]]; then
            echo "    $(basename "$file"): $(sha256sum "$file" | cut -d' ' -f1)" >> "${backup_path}/manifest.yml"
        fi
    done
    
    # Encrypt if needed
    if [[ "$OPC_BACKUP_ENCRYPT" == "true" ]]; then
        log_info "Encrypting backup..."
        local key_file="$(opc_get_customer_dir "$OPC_ID" vault)/encrypted/keys/backup-key"
        if [[ -f "$key_file" ]]; then
            for file in "${backup_path}"/*.tar.gz; do
                if [[ -f "$file" ]]; then
                    gpg --symmetric --cipher-algo AES256 --passphrase-file "$key_file" \
                        --batch --yes -o "${file}.gpg" "$file"
                    rm "$file"
                fi
            done
        else
            log_warn "Encryption key not found, backup is unencrypted"
        fi
    fi
    
    # Upload if needed
    if [[ "$REMOTE_UPLOAD" == "true" ]]; then
        log_info "Uploading to remote storage..."
        rclone sync "$backup_path" "remote:opc200-backups/${OPC_ID}/" --progress
    fi
    
    ln -sfn "$backup_path" "${backup_dir}/latest"
    echo "COMPLETED" > "${backup_path}/.backup_status"
    
    log_success "Backup complete: $backup_path ($(du -sh "$backup_path" | cut -f1))"
}

# Restore backup
restore_backup() {
    if [[ -z "$BACKUP_NAME" ]]; then
        log_error "Restore requires --name"
        exit 1
    fi
    
    local backup_dir=$(get_backup_dir)
    local backup_path="${backup_dir}/${BACKUP_NAME}"
    local data_dir=$(get_data_dir)
    
    if [[ ! -d "$backup_path" ]]; then
        log_error "Backup not found: $backup_path"
        exit 1
    fi
    
    log_warn "About to restore: $BACKUP_NAME"
    log_warn "Current data will be overwritten!"
    read -p "Confirm restore? (yes/no): " confirm
    [[ "$confirm" == "yes" ]] || { log_info "Cancelled"; exit 0; }
    
    [[ "$OPC_DRY_RUN" == "true" ]] && { log_warn "[DRY-RUN] Would restore from: $backup_path"; return 0; }
    
    # Emergency backup
    log_info "Creating emergency backup of current state..."
    BACKUP_NAME="pre-restore-$(date +%Y%m%d-%H%M%S)"
    create_backup
    
    local container_name="opc200-${OPC_ID,,}-gateway"
    docker stop "$container_name" 2>/dev/null || true
    
    # Decrypt if needed
    if [[ -f "${backup_path}/data.tar.gz.gpg" ]]; then
        log_info "Decrypting backup..."
        local key_file="$(opc_get_customer_dir "$OPC_ID" vault)/encrypted/keys/backup-key"
        for file in "${backup_path}"/*.gpg; do
            [[ -f "$file" ]] && gpg --decrypt --passphrase-file "$key_file" --batch --yes -o "${file%.gpg}" "$file"
        done
    fi
    
    # Restore
    [[ -f "${backup_path}/data.tar.gz" ]] && {
        rm -rf "${data_dir}.old"
        mv "$data_dir" "${data_dir}.old" 2>/dev/null || true
        mkdir -p "$data_dir"
        tar -xzf "${backup_path}/data.tar.gz" -C "$(dirname "$data_dir")"
    }
    
    [[ -f "${backup_path}/config.tar.gz" ]] && tar -xzf "${backup_path}/config.tar.gz" -C "$(opc_get_customer_dir "$OPC_ID" base)"
    [[ -f "${backup_path}/skills.tar.gz" ]] && tar -xzf "${backup_path}/skills.tar.gz" -C "$(opc_get_customer_dir "$OPC_ID" base)"
    
    docker start "$container_name" 2>/dev/null || log_warn "Gateway start failed"
    log_success "Restore complete! Original data at: ${data_dir}.old"
}

# List backups
list_backups() {
    local backup_dir=$(get_backup_dir)
    [[ -d "$backup_dir" ]] || { log_error "Backup directory not found"; exit 1; }
    
    log_info "Backups for ${OPC_ID}:"
    echo "========================================"
    printf "%-25s %-10s %-12s\n" "NAME" "SIZE" "STATUS"
    echo "----------------------------------------"
    
    for backup in "$backup_dir"/auto-*; do
        [[ -d "$backup" ]] || continue
        local name=$(basename "$backup")
        local size=$(du -sh "$backup" | cut -f1)
        local status=$(cat "${backup}/.backup_status" 2>/dev/null || echo "?")
        printf "%-25s %-10s %-12s\n" "$name" "$size" "$status"
    done
    
    [[ -L "${backup_dir}/latest" ]] && echo "" && log_info "Latest: $(basename "$(readlink "${backup_dir}/latest")")"
}

# Cleanup old backups
cleanup_backups() {
    local backup_dir=$(get_backup_dir)
    log_info "Cleaning up backups older than $OPC_BACKUP_RETENTION_DAYS days"
    
    local deleted=0
    while IFS= read -r backup; do
        [[ -d "$backup" ]] || continue
        log_info "Deleting: $(basename "$backup")"
        [[ "$OPC_DRY_RUN" == "true" ]] && continue
        rm -rf "$backup"
        ((deleted++))
    done <<< "$(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" -mtime +${OPC_BACKUP_RETENTION_DAYS} 2>/dev/null)"
    
    log_success "Cleanup complete, deleted $deleted backups"
}

# Main
main() {
    log_info "OPC200 Backup Manager"
    log_info "====================="
    
    parse_args "$@"
    opc_init_config "$CONFIG_FILE"
    setup_dirs
    check_dependencies
    
    log_info "Customer: $OPC_ID"
    log_info "Action: $ACTION"
    log_info "Encryption: $OPC_BACKUP_ENCRYPT"
    [[ "$REMOTE_UPLOAD" == "true" ]] && log_info "Remote upload: enabled"
    
    case "$ACTION" in
        backup) create_backup ;;
        restore) restore_backup ;;
        list) list_backups ;;
        cleanup) cleanup_backups ;;
        *) log_error "Unknown action: $ACTION"; exit 1 ;;
    esac
}

main "$@"
