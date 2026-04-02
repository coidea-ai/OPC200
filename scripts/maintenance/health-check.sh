#!/bin/bash
#
# OPC200 Health Check Script
# Usage: ./health-check.sh [--env production] [--batch N] [--full]
#

set -euo pipefail

# Source common logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"

# Default values
ENV="staging"
BATCH=""
FULL=false
TIMEOUT=30
ALERT_THRESHOLD=80  # Alert if health score below 80%
MAX_PARALLEL=10     # Maximum parallel checks

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
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --parallel)
            MAX_PARALLEL="$2"
            shift 2
            ;;
        --dry-run)
            export OPC_DRY_RUN="true"
            shift
            ;;
        --verbose|-v)
            export OPC_LOG_LEVEL="DEBUG"
            shift
            ;;
        --help)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --env ENV        Environment (default: staging)
  --batch N        Check specific batch only
  --full           Run full diagnostic checks
  --timeout SEC    Connection timeout (default: 30)
  --parallel N     Max parallel checks (default: 10)
  --dry-run        Simulate run without making actual requests
  -v, --verbose    Enable debug logging
  --help           Show this help

Examples:
  # Check staging environment
  $0 --env staging
  
  # Check production batch 1 with 20 parallel workers
  $0 --env production --batch 1 --parallel 20
  
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

# Health check functions
check_service_health() {
    local customer_id=$1
    local endpoint=$2
    
    # Check Gateway health with retry
    local gateway_status
    local attempt=1
    local max_attempts=3
    
    while [[ $attempt -le $max_attempts ]]; do
        gateway_status=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time $TIMEOUT \
            "$endpoint/health" 2>/dev/null || echo "000")
        
        if [[ "$gateway_status" == "200" ]]; then
            break
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_debug "Gateway check failed (attempt $attempt/$max_attempts), retrying..."
            sleep 1
        fi
        ((attempt++))
    done
    
    if [[ "$gateway_status" == "200" ]]; then
        echo "HEALTHY"
    else
        echo "UNHEALTHY:$gateway_status"
    fi
}

check_skill_health() {
    local customer_id=$1
    local skill_name=$2
    
    # Mock skill health check - in production this would call the actual skill
    # For now, assume skills are healthy if Gateway is healthy
    echo "HEALTHY"
}

check_database() {
    local customer_id=$1
    
    # Check SQLite database integrity
    local db_path="/data/opc200/$customer_id/journal/journal.db"
    
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
    
    # Get disk usage percentage
    local usage
    usage=$(df /data/opc200 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "100")
    
    if [[ $usage -lt $threshold ]]; then
        echo "HEALTHY:$usage"
    else
        echo "WARNING:$usage"
    fi
}

check_memory() {
    local customer_id=$1
    
    # Get memory usage
    local usage
    usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}' 2>/dev/null || echo "100")
    
    if [[ $usage -lt 90 ]]; then
        echo "HEALTHY:$usage"
    else
        echo "WARNING:$usage"
    fi
}

check_backup_status() {
    local customer_id=$1
    
    # Check if backup exists and is recent (within 24 hours)
    local backup_dir="/data/opc200/$customer_id/backups"
    local recent_backup
    
    recent_backup=$(find "$backup_dir" -name "*.db" -mtime -1 2>/dev/null | head -1)
    
    if [[ -n "$recent_backup" ]]; then
        echo "HEALTHY"
    else
        echo "STALE"
    fi
}

# Worker function for parallel health checks (runs in subshell)
run_health_check_worker() {
    local customer_id=$1
    local customer_code="OPC-$(printf "%03d" $customer_id)"
    local report_dir="$2"
    
    log_debug "[$customer_code] Running health checks..."
    
    # Determine endpoint based on deployment type
    local endpoint
    if [[ $customer_id -le 150 ]]; then
        # On-premise: Tailscale IP
        endpoint="http://opc-${customer_id}.tailnet.opc200.local"
    else
        # Cloud: Public endpoint
        endpoint="https://${customer_code}.opc200.coidea.ai"
    fi
    
    # Dry run mode - just log and return mock result
    if [[ "${OPC_DRY_RUN:-false}" == "true" ]]; then
        log_info "[DRY-RUN] [$customer_code] Would check: $endpoint"
        cat > "$report_dir/${customer_code}.json" << EOF
{
    "customer_id": "$customer_code",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "health_score": 100,
    "checks": {
        "gateway": "HEALTHY",
        "database": "HEALTHY",
        "disk": "HEALTHY:50",
        "memory": "HEALTHY:60",
        "backup": "HEALTHY",
        "skills": "HEALTHY"
    },
    "status": "HEALTHY",
    "dry_run": true
}
EOF
        echo "$customer_code|HEALTHY|100"
        return 0
    fi
    
    # Run checks
    local gateway_health
    gateway_health=$(check_service_health "$customer_id" "$endpoint")
    
    local db_health
    db_health=$(check_database "$customer_id")
    
    local disk_health
    disk_health=$(check_disk_space "$customer_id")
    
    local memory_health
    memory_health=$(check_memory "$customer_id")
    
    local backup_health
    backup_health=$(check_backup_status "$customer_id")
    
    # Check skills
    local skills_health="HEALTHY"
    for skill in opc-journal-core opc-pattern-recognition opc-milestone-tracker opc-async-task-manager opc-insight-generator; do
        local skill_status
        skill_status=$(check_skill_health "$customer_id" "$skill")
        if [[ "$skill_status" != "HEALTHY" ]]; then
            skills_health="UNHEALTHY:$skill"
            break
        fi
    done
    
    # Calculate overall health score
    local score=100
    [[ "$gateway_health" != "HEALTHY" ]] && score=$((score - 30))
    [[ "$db_health" != "HEALTHY" ]] && score=$((score - 20))
    [[ "$disk_health" != HEALTHY:* ]] && score=$((score - 15))
    [[ "$memory_health" != HEALTHY:* ]] && score=$((score - 15))
    [[ "$backup_health" != "HEALTHY" ]] && score=$((score - 10))
    [[ "$skills_health" != "HEALTHY" ]] && score=$((score - 10))
    
    # Determine status
    local status
    if [[ $score -ge 80 ]]; then
        status="HEALTHY"
    elif [[ $score -ge 50 ]]; then
        status="DEGRADED"
    else
        status="CRITICAL"
    fi
    
    # Save individual report
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
    
    # Output summary for parent process
    echo "$customer_code|$status|$score"
}

export -f run_health_check_worker check_service_health check_skill_health check_database check_disk_space check_memory check_backup_status
export -f log_debug log_info log_warn log_error
export OPC_DRY_RUN OPC_LOG_LEVEL TIMEOUT

# Determine customer range
if [[ -n "$BATCH" ]]; then
    # Check specific batch (50 customers per batch)
    START_ID=$(( (BATCH - 1) * 50 + 1 ))
    END_ID=$(( BATCH * 50 ))
else
    # Check all based on environment
    case $ENV in
        staging)
            START_ID=1
            END_ID=5
            ;;
        pilot)
            START_ID=1
            END_ID=10
            ;;
        production)
            START_ID=1
            END_ID=200
            ;;
        *)
            log_error "Unknown environment: $ENV"
            exit 1
            ;;
    esac
fi

log_info "=========================================="
log_info "OPC200 Health Check"
log_info "=========================================="
log_info "Environment: $ENV"
log_info "Range: OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)"
[[ -n "$BATCH" ]] && log_info "Batch: $BATCH"
$FULL && log_info "Mode: FULL diagnostic"
log_info "Parallel workers: $MAX_PARALLEL"
[[ "${OPC_DRY_RUN:-false}" == "true" ]] && log_warn "Mode: DRY RUN (no actual checks)"
log_info "=========================================="

# Create report directory
REPORT_DIR="./logs/health-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT_DIR"

# Statistics
declare -i HEALTHY=0
declare -i DEGRADED=0
declare -i CRITICAL=0
declare -a CRITICAL_IDS=()

# Generate ID list for parallel processing
ID_LIST=$(seq $START_ID $END_ID)

# Check if GNU parallel is available
if command -v parallel >/dev/null 2>&1; then
    log_info "Using GNU parallel for parallel execution"
    
    # Run health checks in parallel using GNU parallel
    RESULTS=$(echo "$ID_LIST" | parallel -j "$MAX_PARALLEL" run_health_check_worker {} "$REPORT_DIR")
    
    # Process results
    while IFS='|' read -r customer_code status score; do
        case $status in
            HEALTHY)
                ((HEALTHY++))
                log_info "[$customer_code] ✅ HEALTHY (score: $score)"
                ;;
            DEGRADED)
                ((DEGRADED++))
                log_warn "[$customer_code] ⚠️ DEGRADED (score: $score)"
                ;;
            CRITICAL)
                ((CRITICAL++))
                CRITICAL_IDS+=($customer_code)
                log_error "[$customer_code] ❌ CRITICAL (score: $score)"
                ;;
        esac
    done <<< "$RESULTS"
else
    log_warn "GNU parallel not found, falling back to sequential execution"
    
    # Run sequentially
    for i in $ID_LIST; do
        result=$(run_health_check_worker $i "$REPORT_DIR")
        
        # Parse result
        customer_code=$(echo "$result" | cut -d'|' -f1)
        status=$(echo "$result" | cut -d'|' -f2)
        score=$(echo "$result" | cut -d'|' -f3)
        
        case $status in
            HEALTHY)
                ((HEALTHY++))
                log_info "[$customer_code] ✅ HEALTHY (score: $score)"
                ;;
            DEGRADED)
                ((DEGRADED++))
                log_warn "[$customer_code] ⚠️ DEGRADED (score: $score)"
                ;;
            CRITICAL)
                ((CRITICAL++))
                CRITICAL_IDS+=($customer_code)
                log_error "[$customer_code] ❌ CRITICAL (score: $score)"
                ;;
        esac
    done
fi

# Generate summary report
TOTAL=$((END_ID - START_ID + 1))
SUMMARY_FILE="$REPORT_DIR/summary.json"

cat > "$SUMMARY_FILE" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "environment": "$ENV",
    "batch": ${BATCH:-null},
    "range": {
        "start": "OPC-$(printf "%03d" $START_ID)",
        "end": "OPC-$(printf "%03d" $END_ID)"
    },
    "summary": {
        "total": $TOTAL,
        "healthy": $HEALTHY,
        "degraded": $DEGRADED,
        "critical": $CRITICAL
    },
    "percentages": {
        "healthy": $(awk "BEGIN {printf \"%.1f\", ($HEALTHY/$TOTAL)*100}"),
        "degraded": $(awk "BEGIN {printf \"%.1f\", ($DEGRADED/$TOTAL)*100}"),
        "critical": $(awk "BEGIN {printf \"%.1f\", ($CRITICAL/$TOTAL)*100}")
    },
    "critical_ids": [$(printf '"%s",' "${CRITICAL_IDS[@]}" | sed 's/,$//')]
}
EOF

# Print summary
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
    for id in "${CRITICAL_IDS[@]}"; do
        log_error "  - $id"
    done
    log_info "Details: $REPORT_DIR/"
    exit 1
fi

log_success "All instances are healthy!"
log_info "Report: $SUMMARY_FILE"
exit 0
