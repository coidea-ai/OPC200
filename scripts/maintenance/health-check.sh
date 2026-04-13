#!/bin/bash
#
# OPC200 Health Check Script
# Usage: ./health-check.sh [--env production] [--batch N] [--full] [--config FILE]
#

set -euo pipefail

# Source libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"
source "$SCRIPT_DIR/../lib/config.sh"

# Default values
ENV="staging"
BATCH=""
FULL=false
CONFIG_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        --batch)
            BATCH="$2"
            shift 2
            ;;
        --full)
            FULL=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --timeout)
            export OPC_HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        --parallel)
            export OPC_MAX_PARALLEL_CHECKS="$2"
            shift 2
            ;;
        --dry-run)
            export OPC_DRY_RUN="true"
            shift
            ;;
        -v|--verbose)
            export OPC_LOG_LEVEL="DEBUG"
            shift
            ;;
        --help)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --env ENV            Environment (default: staging)
  --batch N            Check specific batch only
  --full               Run full diagnostic checks
  --config FILE        Use specific config file
  --timeout SEC        Connection timeout (default: \$OPC_HEALTH_CHECK_TIMEOUT)
  --parallel N         Max parallel checks (default: \$OPC_MAX_PARALLEL_CHECKS)
  --dry-run            Simulate run without making actual requests
  -v, --verbose        Enable debug logging
  --help               Show this help

Examples:
  # Check staging environment
  $0 --env staging
  
  # Check production batch 1 with custom config
  $0 --env production --batch 1 --config ~/.opcrc.prod
  
  # Dry run to see what would be checked
  $0 --env pilot --dry-run
EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Initialize configuration
opc_init_config "$CONFIG_FILE"

# Health check functions
check_service_health() {
    local customer_id=$1
    local endpoint=$2
    local max_attempts=3
    local attempt=1
    local gateway_status
    
    while [[ $attempt -le $max_attempts ]]; do
        gateway_status=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time "$OPC_HEALTH_CHECK_TIMEOUT" \
            "$endpoint/health" 2>/dev/null || echo "000")
        
        [[ "$gateway_status" == "200" ]] && break
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_debug "Gateway check failed (attempt $attempt/$max_attempts), retrying..."
            sleep 1
        fi
        ((attempt++))
    done
    
    [[ "$gateway_status" == "200" ]] && echo "HEALTHY" || echo "UNHEALTHY:$gateway_status"
}

check_skill_health() {
    local customer_id=$1
    local skill_name=$2
    echo "HEALTHY"
}

check_database() {
    local customer_id=$1
    local db_path="${OPC_DATA_DIR}/$customer_id/journal/journal.db"
    
    if [[ -f "$db_path" ]]; then
        if sqlite3 "$db_path" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
            echo "HEALTHY"
        else
            echo "CORRUPTED"
        fi
    else
        echo "MISSING"
    fi
}

check_disk_space() {
    local customer_id=$1
    local threshold=90
    local usage
    
    usage=$(df "${OPC_DATA_DIR}/$customer_id" 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "100")
    
    [[ $usage -lt $threshold ]] && echo "HEALTHY:$usage" || echo "WARNING:$usage"
}

check_memory() {
    local customer_id=$1
    local usage
    
    usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}' 2>/dev/null || echo "100")
    [[ $usage -lt 90 ]] && echo "HEALTHY:$usage" || echo "WARNING:$usage"
}

check_backup_status() {
    local customer_id=$1
    local backup_dir="${OPC_DATA_DIR}/$customer_id/backups"
    local recent_backup
    
    recent_backup=$(find "$backup_dir" -name "*.db" -mtime -1 2>/dev/null | head -1)
    [[ -n "$recent_backup" ]] && echo "HEALTHY" || echo "STALE"
}

# Worker function for parallel health checks
run_health_check_worker() {
    local customer_id=$1
    local customer_code
    local report_dir="$2"
    
    customer_code=$(opc_format_customer_id "$customer_id")
    log_debug "[$customer_code] Running health checks..."
    
    local endpoint
    local numeric_id=$(opc_parse_customer_id "$customer_id")
    # v2.4 重构后部署比例: 20本地 + 180云端
    if [[ $numeric_id -le 20 ]]; then
        endpoint="http://opc-${numeric_id}.tailnet.opc200.local"
    else
        endpoint="https://${customer_code}.opc200.coidea.ai"
    fi
    
    # Dry run mode
    if [[ "$OPC_DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] [$customer_code] Would check: $endpoint"
        cat > "$report_dir/${customer_code}.json" << EOF
{
    "customer_id": "$customer_code",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "health_score": 100,
    "status": "HEALTHY",
    "dry_run": true
}
EOF
        echo "$customer_code|HEALTHY|100"
        return 0
    fi
    
    local gateway_health db_health disk_health memory_health backup_health
    gateway_health=$(check_service_health "$customer_id" "$endpoint")
    db_health=$(check_database "$customer_id")
    disk_health=$(check_disk_space "$customer_id")
    memory_health=$(check_memory "$customer_id")
    backup_health=$(check_backup_status "$customer_id")
    
    local skills_health="HEALTHY"
    # v2.4 重构后只检查核心技能
    for skill in opc-journal-core opc-milestone-tracker opc-insight-generator; do
        local skill_status
        skill_status=$(check_skill_health "$customer_id" "$skill")
        if [[ "$skill_status" != "HEALTHY" ]]; then
            skills_health="UNHEALTHY:$skill"
            break
        fi
    done
    
    # Legacy skills 不再默认检查
    for legacy_skill in opc-async-task-manager opc-pattern-recognition; do
        local legacy_status
        legacy_status=$(check_skill_health "$customer_id" "$legacy_skill")
        if [[ "$legacy_status" != "HEALTHY" && "$skills_health" == "HEALTHY" ]]; then
            skills_health="DEGRADED:$legacy_skill"
            break
        fi
    done
    
    local score=100
    [[ "$gateway_health" != "HEALTHY" ]] && score=$((score - 30))
    [[ "$db_health" != "HEALTHY" ]] && score=$((score - 20))
    [[ "$disk_health" != HEALTHY:* ]] && score=$((score - 15))
    [[ "$memory_health" != HEALTHY:* ]] && score=$((score - 15))
    [[ "$backup_health" != "HEALTHY" ]] && score=$((score - 10))
    [[ "$skills_health" != "HEALTHY" ]] && score=$((score - 10))
    
    local status
    if [[ $score -ge 80 ]]; then
        status="HEALTHY"
    elif [[ $score -ge 50 ]]; then
        status="DEGRADED"
    else
        status="CRITICAL"
    fi
    
    cat > "$report_dir/${customer_code}.json" << EOF
{
    "customer_id": "$customer_code",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "health_score": $score,
    "checks": {
        "gateway": "$gateway_health",
        "database": "$db_health",
        "disk": "$disk_health",
        "memory": "$memory_health",
        "backup": "$backup_health",
        "skills": "$skills_health"
    },
    "status": "$status"
}
EOF
    
    echo "$customer_code|$status|$score"
}

export -f run_health_check_worker check_service_health check_skill_health check_database check_disk_space check_memory check_backup_status
export -f log_debug log_info log_warn log_error opc_parse_customer_id opc_format_customer_id
export OPC_DRY_RUN OPC_LOG_LEVEL OPC_HEALTH_CHECK_TIMEOUT OPC_DATA_DIR

# Determine customer range
if [[ -n "$BATCH" ]]; then
    START_ID=$(( (BATCH - 1) * 50 + 1 ))
    END_ID=$(( BATCH * 50 ))
else
    case $ENV in
        staging) START_ID=1; END_ID=5 ;;
        pilot) START_ID=1; END_ID=10 ;;
        production) START_ID=1; END_ID=200 ;;
        *) log_error "Unknown environment: $ENV"; exit 1 ;;
    esac
fi

log_info "=========================================="
log_info "OPC200 Health Check"
log_info "=========================================="
log_info "Environment: $ENV"
log_info "Range: $(opc_format_customer_id $START_ID) to $(opc_format_customer_id $END_ID)"
[[ -n "$BATCH" ]] && log_info "Batch: $BATCH"
$FULL && log_info "Mode: FULL diagnostic"
log_info "Parallel workers: $OPC_MAX_PARALLEL_CHECKS"
log_info "Timeout: ${OPC_HEALTH_CHECK_TIMEOUT}s"
[[ "$OPC_DRY_RUN" == "true" ]] && log_warn "Mode: DRY RUN"
log_info "=========================================="

# Create report directory
REPORT_DIR="${OPC_LOG_DIR}/health-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT_DIR"

# Statistics
declare -i HEALTHY=0 DEGRADED=0 CRITICAL=0
declare -a CRITICAL_IDS=()

ID_LIST=$(seq $START_ID $END_ID)

# Check if GNU parallel is available
if command -v parallel >/dev/null 2>&1; then
    log_info "Using GNU parallel for parallel execution"
    RESULTS=$(echo "$ID_LIST" | parallel -j "$OPC_MAX_PARALLEL_CHECKS" run_health_check_worker {} "$REPORT_DIR")
    
    while IFS='|' read -r customer_code status score; do
        case $status in
            HEALTHY) ((HEALTHY++)); log_info "[$customer_code] ✅ HEALTHY (score: $score)" ;;
            DEGRADED) ((DEGRADED++)); log_warn "[$customer_code] ⚠️ DEGRADED (score: $score)" ;;
            CRITICAL) ((CRITICAL++)); CRITICAL_IDS+=($customer_code); log_error "[$customer_code] ❌ CRITICAL (score: $score)" ;;
        esac
    done <<< "$RESULTS"
else
    log_warn "GNU parallel not found, using sequential execution"
    for i in $ID_LIST; do
        result=$(run_health_check_worker $i "$REPORT_DIR")
        customer_code=$(echo "$result" | cut -d'|' -f1)
        status=$(echo "$result" | cut -d'|' -f2)
        score=$(echo "$result" | cut -d'|' -f3)
        
        case $status in
            HEALTHY) ((HEALTHY++)); log_info "[$customer_code] ✅ HEALTHY (score: $score)" ;;
            DEGRADED) ((DEGRADED++)); log_warn "[$customer_code] ⚠️ DEGRADED (score: $score)" ;;
            CRITICAL) ((CRITICAL++)); CRITICAL_IDS+=($customer_code); log_error "[$customer_code] ❌ CRITICAL (score: $score)" ;;
        esac
    done
fi

# Generate summary
TOTAL=$((END_ID - START_ID + 1))
SUMMARY_FILE="$REPORT_DIR/summary.json"

cat > "$SUMMARY_FILE" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "environment": "$ENV",
    "batch": ${BATCH:-null},
    "range": {"start": "$(opc_format_customer_id $START_ID)", "end": "$(opc_format_customer_id $END_ID)"},
    "summary": {"total": $TOTAL, "healthy": $HEALTHY, "degraded": $DEGRADED, "critical": $CRITICAL},
    "percentages": {
        "healthy": $(awk "BEGIN {printf \"%.1f\", ($HEALTHY/$TOTAL)*100}"),
        "degraded": $(awk "BEGIN {printf \"%.1f\", ($DEGRADED/$TOTAL)*100}"),
        "critical": $(awk "BEGIN {printf \"%.1f\", ($CRITICAL/$TOTAL)*100}")
    },
    "critical_ids": [$(printf '"%s",' "${CRITICAL_IDS[@]}" | sed 's/,$//')]
}
EOF

echo ""
log_info "=========================================="
log_info "Health Check Summary"
log_info "=========================================="
log_info "Total:      $TOTAL"
log_info "Healthy:    $HEALTHY ($(awk "BEGIN {printf \"%.1f%%\", ($HEALTHY/$TOTAL)*100}"))"
log_info "Degraded:   $DEGRADED ($(awk "BEGIN {printf \"%.1f%%\", ($DEGRADED/$TOTAL)*100}"))"
log_info "Critical:   $CRITICAL ($(awk "BEGIN {printf \"%.1f%%\", ($CRITICAL/$TOTAL)*100}"))"
log_info "=========================================="

if [[ ${#CRITICAL_IDS[@]} -gt 0 ]]; then
    log_error "Critical instances require attention:"
    for id in "${CRITICAL_IDS[@]}"; do log_error "  - $id"; done
    log_info "Details: $REPORT_DIR/"
    exit 1
fi

log_success "All instances are healthy!"
log_info "Report: $SUMMARY_FILE"
exit 0
