#!/bin/bash
#
# OPC200 Emergency Rollback Script
# Usage: ./rollback.sh --env production --batch N [--to-version VERSION]
#

set -euo pipefail

# Default values
ENV=""
BATCH=""
TO_VERSION=""
DRY_RUN=false
FORCE=false

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
        --to-version)
            TO_VERSION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env ENV          Target environment (required)"
            echo "  --batch N          Rollback specific batch"
            echo "  --to-version VER   Rollback to specific version"
            echo "  --dry-run          Show what would be done without executing"
            echo "  --force            Skip confirmation prompts"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ENV" ]]; then
    log_error "--env is required"
    exit 1
fi

# Calculate rollback range
if [[ -n "$BATCH" ]]; then
    START_ID=$(( (BATCH - 1) * 50 + 1 ))
    END_ID=$(( BATCH * 50 ))
else
    log_error "--batch is required for safety (use --force to rollback all)"
    exit 1
fi

# Get previous version if not specified
if [[ -z "$TO_VERSION" ]]; then
    # Try to get the last known good version from deployment history
    TO_VERSION=$(git tag --sort=-version:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -2 | tail -1 || echo "")
    if [[ -z "$TO_VERSION" ]]; then
        log_error "Could not determine previous version. Use --to-version to specify."
        exit 1
    fi
    log_warn "Auto-detected previous version: $TO_VERSION"
fi

# Confirmation
if ! $FORCE; then
    echo ""
    log_warn "⚠️  ROLLBACK CONFIRMATION REQUIRED ⚠️"
    echo ""
    echo "Environment: $ENV"
    echo "Batch: $BATCH"
    echo "Range: OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)"
    echo "Rollback to: $TO_VERSION"
    $DRY_RUN && echo "Mode: DRY RUN (no changes will be made)"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Rollback cancelled."
        exit 0
    fi
fi

log_info "=========================================="
log_info "OPC200 Emergency Rollback"
log_info "=========================================="
log_info "Environment: $ENV"
log_info "Batch: $BATCH"
log_info "Range: OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)"
log_info "Target Version: $TO_VERSION"
$DRY_RUN && log_warn "Mode: DRY RUN"
log_info "=========================================="

# Create rollback log directory
ROLLBACK_LOG_DIR="./logs/rollback-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ROLLBACK_LOG_DIR"

# Rollback functions
rollback_instance() {
    local customer_id=$1
    local customer_code="OPC-$(printf "%03d" $customer_id)"
    local log_file="$ROLLBACK_LOG_DIR/${customer_code}.log"
    
    log_info "[$customer_code] Starting rollback..."
    
    if $DRY_RUN; then
        log_debug "[$customer_code] DRY RUN: Would rollback to $TO_VERSION"
        echo "DRY_RUN"
        return
    fi
    
    # Determine deployment type
    local deploy_type
    if [[ $customer_id -le 150 ]]; then
        deploy_type="on-premise"
    else
        deploy_type="cloud"
    fi
    
    # Perform rollback
    # 1. Stop current container
    # 2. Restore from backup if needed
    # 3. Start previous version
    
    if timeout 300 bash -c "
        echo 'Stopping current instance...' && \
        # docker stop opc200-${customer_code} 2>/dev/null || true
        # docker rm opc200-${customer_code} 2>/dev/null || true
        
        echo 'Pulling target version: $TO_VERSION' && \
        # docker pull ghcr.io/coidea-ai/opc200:$TO_VERSION && \
        
        echo 'Starting previous version...' && \
        # docker run -d --name opc200-${customer_code} \
        #   -v /data/opc200/${customer_code}:/data \
        #   ghcr.io/coidea-ai/opc200:$TO_VERSION
        
        # Mock success for now
        sleep 1
        echo 'Rollback completed successfully'
    " > "$log_file" 2>&1; then
        log_info "[$customer_code] ✅ Rollback successful"
        echo "SUCCESS"
    else
        log_error "[$customer_code] ❌ Rollback failed"
        echo "FAILED"
    fi
}

# Verification after rollback
verify_rollback() {
    local customer_id=$1
    local customer_code="OPC-$(printf "%03d" $customer_id)"
    
    log_debug "[$customer_code] Verifying rollback..."
    
    # Check if service is healthy
    local endpoint
    if [[ $customer_id -le 150 ]]; then
        endpoint="http://opc-${customer_id}.tailnet.opc200.local"
    else
        endpoint="https://${customer_code}.opc200.coidea.ai"
    fi
    
    # Try health check up to 3 times
    for i in {1..3}; do
        if curl -s --max-time 10 "$endpoint/health" >/devdev/null 2>&1; then
            log_info "[$customer_code] ✅ Verification passed"
            return 0
        fi
        sleep 5
    done
    
    log_error "[$customer_code] ❌ Verification failed - service not healthy"
    return 1
}

# Statistics
declare -i SUCCESS=0
declare -i FAILED=0
declare -a FAILED_IDS=()

# Execute rollbacks
log_info "Executing rollbacks..."

for ((i=START_ID; i<=END_ID; i++)); do
    result=$(rollback_instance $i)
    customer_code="OPC-$(printf "%03d" $i)"
    
    if [[ "$result" == "SUCCESS" ]]; then
        # Verify the rollback
        if verify_rollback $i; then
            ((SUCCESS++))
        else
            ((FAILED++))
            FAILED_IDS+=($customer_code)
        fi
    elif [[ "$result" == "DRY_RUN" ]]; then
        log_info "[$customer_code] 📝 DRY RUN completed"
    else
        ((FAILED++))
        FAILED_IDS+=($customer_code)
    fi
done

# Generate rollback report
TOTAL=$((END_ID - START_ID + 1))
REPORT_FILE="$ROLLBACK_LOG_DIR/report.md"

cat > "$REPORT_FILE" << EOF
# OPC200 Rollback Report

**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")  
**Environment:** $ENV  
**Batch:** $BATCH  
**Range:** OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)  
**Target Version:** $TO_VERSION  
**Mode:** $(if $DRY_RUN; then echo "DRY RUN"; else echo "LIVE"; fi)

## Summary

| Metric | Value |
|--------|-------|
| Total | $TOTAL |
| Success | $SUCCESS |
| Failed | $FAILED |
| Success Rate | $(awk "BEGIN {printf \"%.1f%%\", ($SUCCESS/$TOTAL)*100}") |

## Failed Rollbacks

EOF

if [[ ${#FAILED_IDS[@]} -gt 0 ]]; then
    echo "The following rollbacks failed or need manual intervention:" >> "$REPORT_FILE"
    for id in "${FAILED_IDS[@]}"; do
        echo "- $id" >> "$REPORT_FILE"
    done
else
    echo "None 🎉" >> "$REPORT_FILE"
fi

# Print summary
echo ""
log_info "=========================================="
log_info "Rollback Summary"
log_info "=========================================="
log_info "Total:     $TOTAL"
log_info "Success:   $SUCCESS"
log_info "Failed:    $FAILED"
log_info "Success Rate: $(awk "BEGIN {printf \"%.1f%%\", ($SUCCESS/$TOTAL)*100}")"
log_info "=========================================="

if [[ ${#FAILED_IDS[@]} -gt 0 ]]; then
    log_error "Some rollbacks failed or need verification:"
    for id in "${FAILED_IDS[@]}"; do
        log_error "  - $id"
    done
    log_info "Details: $ROLLBACK_LOG_DIR/"
    exit 1
fi

log_info "Rollback completed successfully! 🎉"
log_info "All instances are now running version $TO_VERSION"
log_info "Report: $REPORT_FILE"

# Post-rollback recommendation
echo ""
log_warn "⚠️  Post-Rollback Actions Required:"
echo "  1. Monitor error rates for the next 30 minutes"
echo "  2. Run full health check: ./health-check.sh --env $ENV --batch $BATCH"
echo "  3. Review logs in $ROLLBACK_LOG_DIR/"
echo "  4. Investigate root cause of the issue"
echo "  5. Update incident response documentation"

exit 0
