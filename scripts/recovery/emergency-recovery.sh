#!/bin/bash
#===============================================================================
# OPC200 Emergency Recovery Script
#===============================================================================

set -euo pipefail

# Source libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"
source "$SCRIPT_DIR/../lib/config.sh"

# Configuration
OPC_ID=""
SCENARIO=""
NOTIFY=true
CONFIG_FILE=""

SCENARIOS=(gateway-failure data-vault-corruption tailscale-disconnect disk-full memory-exhausted)

show_help() {
    cat << EOF
OPC200 Emergency Recovery

Usage: $0 --id OPC-XXX --scenario SCENARIO [OPTIONS]

SCENARIOS:
    gateway-failure       Gateway failure
    data-vault-corruption Data vault corruption
    tailscale-disconnect  Tailscale connection lost
    disk-full             Disk full
    memory-exhausted      Memory exhausted

OPTIONS:
    --id ID           Customer ID (required)
    --scenario NAME   Recovery scenario (required)
    --config FILE     Use specific config file
    --dry-run         Simulate without actual execution
    --no-notify       Disable notifications
    -v, --verbose     Enable debug logging
    -h, --help        Show this help

Examples:
    $0 --id OPC-001 --scenario gateway-failure
    $0 --id OPC-001 --scenario disk-full --dry-run
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --id) OPC_ID="$2"; shift 2 ;;
            --scenario) SCENARIO="$2"; shift 2 ;;
            --config) CONFIG_FILE="$2"; shift 2 ;;
            --dry-run) export OPC_DRY_RUN="true"; log_warn "Dry run mode"; shift ;;
            --no-notify) NOTIFY=false; shift ;;
            -v|--verbose) export OPC_LOG_LEVEL="DEBUG"; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) log_error "Unknown parameter: $1"; exit 1 ;;
        esac
    done

    if [[ -z "$OPC_ID" ]] || [[ -z "$SCENARIO" ]]; then
        log_error "Missing required parameters (--id, --scenario)"
        exit 1
    fi
    
    if ! opc_validate_customer_id "$OPC_ID"; then
        log_error "Invalid customer ID: $OPC_ID"
        exit 1
    fi
    
    if [[ ! " ${SCENARIOS[@]} " =~ " ${SCENARIO} " ]]; then
        log_error "Unknown scenario: $SCENARIO"
        log_info "Available: ${SCENARIOS[*]}"
        exit 1
    fi
}

# Execute command with retry
run_cmd() {
    local cmd="$1" desc="${2:-$cmd}" max_retries="${3:-1}" retry_delay="${4:-2}"
    log_info "Executing: $desc"
    
    [[ "$OPC_DRY_RUN" == "true" ]] && { log_warn "[DRY-RUN] $cmd"; return 0; }
    
    local attempt=1
    while [[ $attempt -le $max_retries ]]; do
        log_debug "Attempt $attempt/$max_retries"
        eval "$cmd" && return 0
        local exit_code=$?
        [[ $attempt -lt $max_retries ]] && { log_warn "Failed, retrying in ${retry_delay}s..."; sleep $retry_delay; retry_delay=$((retry_delay*2)); }
        ((attempt++))
    done
    log_error "Failed after $max_retries attempts"
    return 1
}

# Notify customer
notify_customer() {
    local message="$1"
    [[ "$NOTIFY" == false ]] && return 0
    log_info "Notifying: $message"
    [[ "$OPC_DRY_RUN" == "true" ]] && { log_warn "[DRY-RUN] Notification simulated"; return 0; }
    log_debug "Notification implementation pending"
}

# Recovery scenarios
recover_gateway_failure() {
    log_warn "Scenario: Gateway failure"
    local container_name="opc200-${OPC_ID,,}-gateway"
    
    run_cmd "docker ps -a --filter name=$container_name --format '{{.Names}}: {{.Status}}'" "Check container status"
    run_cmd "docker logs $container_name --tail 50" "View recent logs" 1 0 || true
    
    if run_cmd "docker restart $container_name" "Restart container" 3 2; then
        sleep 5
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            log_success "Gateway recovered"
            notify_customer "Gateway restarted successfully"
            return 0
        fi
    fi
    
    log_warn "Restart failed, attempting recreate..."
    local compose_file="$(opc_get_customer_dir "$OPC_ID" base)/gateway/docker-compose.yml"
    if [[ -f "$compose_file" ]]; then
        run_cmd "cd $(dirname $compose_file) && docker-compose down && docker-compose up -d" "Recreate container" 2 3
        sleep 10
        if docker ps | grep -q "$container_name"; then
            log_success "Gateway recreated"
            notify_customer "Gateway recreated successfully"
            return 0
        fi
    fi
    
    log_error "Recovery failed, manual intervention needed"
    notify_customer "Gateway recovery failed - manual intervention required"
    return 1
}

recover_data_vault_corruption() {
    log_warn "Scenario: Data vault corruption"
    local vault_dir="$(opc_get_customer_dir "$OPC_ID" vault)"
    local backup_dir="$(opc_get_customer_dir "$OPC_ID" backup)"
    local container_name="opc200-${OPC_ID,,}-gateway"
    
    run_cmd "ls -la ${vault_dir}/" "Check vault directory"
    run_cmd "docker stop $container_name" "Stop Gateway" 2 1 || true
    
    local latest_backup=$(find "$backup_dir" -maxdepth 1 -type d -name "auto-*" | sort | tail -1)
    [[ -z "$latest_backup" ]] && { log_error "No backup available"; return 1; }
    
    log_info "Using backup: $(basename "$latest_backup")"
    
    run_cmd "mv ${vault_dir} ${vault_dir}.corrupted.$(date +%Y%m%d-%H%M%S)" "Move corrupted data"
    run_cmd "mkdir -p ${vault_dir}" "Create new vault"
    
    # Decrypt if needed
    if [[ -f "${latest_backup}/data.tar.gz.gpg" ]]; then
        local key_file="${vault_dir}/encrypted/keys/backup-key"
        [[ -f "$key_file" ]] && gpg --decrypt --passphrase-file "$key_file" --batch --yes -o "${latest_backup}/data.tar.gz" "${latest_backup}/data.tar.gz.gpg"
    fi
    
    [[ -f "${latest_backup}/data.tar.gz" ]] && tar -xzf "${latest_backup}/data.tar.gz" -C "$(dirname "$vault_dir")"
    
    run_cmd "docker start $container_name" "Start Gateway" 3 2
    log_success "Vault restored from backup"
    notify_customer "Data vault restored successfully"
}

recover_tailscale_disconnect() {
    log_warn "Scenario: Tailscale disconnect"
    run_cmd "tailscale status" "Check status" 1 0 || true
    run_cmd "tailscale ip -4" "Get Tailscale IP" 1 0 || true
    
    local auth_key_file="$(opc_get_customer_dir "$OPC_ID" base)/tailscale/auth-key"
    if [[ -f "$auth_key_file" ]]; then
        local auth_key=$(cat "$auth_key_file")
        run_cmd "tailscale down && tailscale up --authkey=$auth_key --accept-routes" "Reconnect" 3 5
    else
        run_cmd "tailscale up --accept-routes" "Attempt reconnect" 2 3
    fi
    
    sleep 5
    if tailscale status >/dev/null 2>&1; then
        log_success "Tailscale reconnected"
        notify_customer "VPN connection restored"
    else
        log_error "Reconnection failed"
        return 1
    fi
}

recover_disk_full() {
    log_warn "Scenario: Disk full"
    run_cmd "df -h /" "Check root partition"
    run_cmd "du -sh $(opc_get_customer_dir "$OPC_ID" base)/* 2>/dev/null | head -10" "Check directory sizes"
    
    # Clean logs
    find "$(opc_get_customer_dir "$OPC_ID" logs)" -name '*.log' -mtime +7 -delete 2>/dev/null || true
    find /var/log -name '*.log' -mtime +7 -delete 2>/dev/null || true
    
    # Clean old backups (keep last 3)
    local backup_dir="$(opc_get_customer_dir "$OPC_ID" backup)"
    find "$backup_dir" -maxdepth 1 -type d -name 'auto-*' | sort | head -n -3 | xargs rm -rf 2>/dev/null || true
    
    # Docker cleanup
    docker system prune -f
    docker volume prune -f 2>/dev/null || true
    
    local usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    if [[ $usage -lt 85 ]]; then
        log_success "Disk space freed (current: ${usage}%)"
        notify_customer "Disk space cleaned, now at ${usage}%"
    else
        log_warn "Disk still critical (${usage}%), consider expansion"
        return 1
    fi
}

recover_memory_exhausted() {
    log_warn "Scenario: Memory exhausted"
    run_cmd "free -h" "Check memory"
    run_cmd "ps aux --sort=-%mem | head -15" "Check memory usage"
    
    local container_name="opc200-${OPC_ID,,}-gateway"
    docker restart "$container_name" 2>/dev/null || true
    
    sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    
    sleep 5
    local mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3*100/$2}')
    if [[ $mem_usage -lt 90 ]]; then
        log_success "Memory freed (current: ${mem_usage}%)"
    else
        log_warn "Memory still critical (${mem_usage}%)"
        return 1
    fi
}

# Log audit
cleanup() {
    local result="${1:-unknown}"
    local audit_dir="customers/on-premise/${OPC_ID}/remote-sessions"
    mkdir -p "$audit_dir"
    cat > "${audit_dir}/emergency-$(date +%Y%m%d-%H%M%S).log" << EOF
---
timestamp: $(date -Iseconds)
operator: $(whoami)
hostname: $(hostname)
scenario: ${SCENARIO}
dry_run: ${OPC_DRY_RUN}
result: ${result}
EOF
}

# Main
main() {
    log_info "OPC200 Emergency Recovery"
    log_info "========================="
    
    parse_args "$@"
    opc_init_config "$CONFIG_FILE"
    
    log_info "Customer: $OPC_ID"
    log_info "Scenario: $SCENARIO"
    
    local result=0
    case "$SCENARIO" in
        gateway-failure) recover_gateway_failure; result=$? ;;
        data-vault-corruption) recover_data_vault_corruption; result=$? ;;
        tailscale-disconnect) recover_tailscale_disconnect; result=$? ;;
        disk-full) recover_disk_full; result=$? ;;
        memory-exhausted) recover_memory_exhausted; result=$? ;;
        *) log_error "Unknown scenario"; exit 1 ;;
    esac
    
    cleanup "$([[ $result -eq 0 ]] && echo "success" || echo "failed")"
    
    [[ $result -eq 0 ]] && log_success "Recovery complete!" || log_error "Recovery failed"
    exit $result
}

main "$@"
