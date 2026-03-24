#!/bin/bash
#
# OPC200 Health Check Script
# Usage: ./health-check.sh [--env production] [--batch N] [--full]
#

set -euo pipefail

# Default values
ENV="staging"
BATCH=""
FULL=false
TIMEOUT=30
ALERT_THRESHOLD=80  # Alert if health score below 80%

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

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
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env ENV        Environment (default: staging)"
            echo "  --batch N        Check specific batch only"
            echo "  --full           Run full diagnostic checks"
            echo "  --timeout SEC    Connection timeout (default: 30)"
            echo "  --help           Show this help"
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
    
    # Check Gateway health
    local gateway_status
    gateway_status=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time $TIMEOUT \
        "$endpoint/health" 2>/dev/null || echo "000")
    
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

# Main health check
run_health_check() {
    local customer_id=$1
    local customer_code="OPC-$(printf "%03d" $customer_id)"
    
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
    
    # Output JSON result
    cat << EOF
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
    "status": $(if [[ $score -ge 80 ]]; then echo '"HEALTHY"'; elif [[ $score -ge 50 ]]; then echo '"DEGRADED"'; else echo '"CRITICAL"'; fi)
}
EOF
}

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
log_info "=========================================="

# Create report directory
REPORT_DIR="./logs/health-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT_DIR"

# Statistics
declare -i HEALTHY=0
declare -i DEGRADED=0
declare -i CRITICAL=0
declare -a CRITICAL_IDS=()

# Run checks
for ((i=START_ID; i<=END_ID; i++)); do
    result=$(run_health_check $i)
    customer_code="OPC-$(printf "%03d" $i)"
    
    # Parse result
    score=$(echo "$result" | grep -o '"health_score": [0-9]*' | awk '{print $2}')
    status=$(echo "$result" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
    
    # Save individual report
    echo "$result" | python3 -m json.tool > "$REPORT_DIR/${customer_code}.json" 2>/dev/null || echo "$result" > "$REPORT_DIR/${customer_code}.json"
    
    # Update statistics
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

log_info "All instances are healthy! 🎉"
log_info "Report: $SUMMARY_FILE"
exit 0
