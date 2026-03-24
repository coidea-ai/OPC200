#!/bin/bash
#
# OPC200 Batch Deployment Script
# Usage: ./batch-deploy.sh --start 1 --count 50 --env production --image ghcr.io/coidea-ai/opc200:latest
#

set -euo pipefail

# Default values
START_ID=1
COUNT=10
ENV="staging"
IMAGE=""
PARALLEL=5
TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --start)
            START_ID="$2"
            shift 2
            ;;
        --count)
            COUNT="$2"
            shift 2
            ;;
        --env)
            ENV="$2"
            shift 2
            ;;
        --image)
            IMAGE="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --start ID       Starting customer ID (default: 1)"
            echo "  --count N        Number of instances to deploy (default: 10)"
            echo "  --env ENV        Environment: staging|pilot|production (default: staging)"
            echo "  --image IMAGE    Container image to deploy (required)"
            echo "  --parallel N     Parallel deployments (default: 5)"
            echo "  --timeout SEC    Timeout per deployment in seconds (default: 300)"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$IMAGE" ]]; then
    log_error "--image is required"
    exit 1
fi

# Calculate end ID
END_ID=$((START_ID + COUNT - 1))

log_info "Starting batch deployment"
log_info "Environment: $ENV"
log_info "Range: OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)"
log_info "Image: $IMAGE"
log_info "Parallel: $PARALLEL"

# Create deployment log directory
DEPLOY_LOG_DIR="./logs/deploy-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEPLOY_LOG_DIR"

# Deployment statistics
declare -i SUCCESS=0
declare -i FAILED=0
declare -a FAILED_IDS=()

# Function to deploy a single instance
deploy_instance() {
    local customer_id=$1
    local customer_code="OPC-$(printf "%03d" $customer_id)"
    local log_file="$DEPLOY_LOG_DIR/${customer_code}.log"
    
    log_info "[$customer_code] Starting deployment..."
    
    # Determine deployment type based on customer ID
    local deploy_type
    if [[ $ENV == "production" ]]; then
        # 150 on-premise, 50 cloud
        if [[ $customer_id -le 150 ]]; then
            deploy_type="on-premise"
        else
            deploy_type="cloud"
        fi
    else
        deploy_type="cloud"
    fi
    
    # Run deployment with timeout
    if timeout $TIMEOUT bash -c "
        ./scripts/deploy/deploy-${deploy_type}.sh \
            --customer-id $customer_code \
            --env $ENV \
            --image $IMAGE \
            2>&1
    " > "$log_file" 2>&1; then
        log_info "[$customer_code] ✅ Deployment successful"
        echo "SUCCESS"
    else
        log_error "[$customer_code] ❌ Deployment failed (exit code: $?)"
        echo "FAILED"
    fi
}

export -f deploy_instance log_info log_error
export ENV IMAGE TIMEOUT DEPLOY_LOG_DIR

# Run deployments in parallel
log_info "Launching deployments (parallel: $PARALLEL)..."

# Generate list of customer IDs
customer_ids=($(seq $START_ID $END_ID))

# Process in batches
for ((i=0; i<${#customer_ids[@]}; i+=PARALLEL)); do
    batch=()
    for ((j=i; j<i+PARALLEL && j<${#customer_ids[@]}; j++)); do
        batch+=(${customer_ids[j]})
    done
    
    log_info "Processing batch: ${batch[*]}"
    
    # Run batch in parallel
    results=$(printf "%s\n" "${batch[@]}" | xargs -P $PARALLEL -I {} bash -c 'deploy_instance "$@"' _ {})
    
    # Process results
    idx=0
    while IFS= read -r result; do
        customer_id=${batch[idx]}
        customer_code="OPC-$(printf "%03d" $customer_id)"
        
        if [[ "$result" == "SUCCESS" ]]; then
            ((SUCCESS++))
        else
            ((FAILED++))
            FAILED_IDS+=($customer_code)
        fi
        ((idx++))
    done <<< "$results"
done

# Generate deployment report
REPORT_FILE="$DEPLOY_LOG_DIR/report.md"
cat > "$REPORT_FILE" << EOF
# OPC200 Batch Deployment Report

**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")  
**Environment:** $ENV  
**Image:** $IMAGE  
**Range:** OPC-$(printf "%03d" $START_ID) to OPC-$(printf "%03d" $END_ID)

## Summary

| Metric | Value |
|--------|-------|
| Total | $COUNT |
| Success | $SUCCESS |
| Failed | $FAILED |
| Success Rate | $(awk "BEGIN {printf \"%.1f%%\", ($SUCCESS/$COUNT)*100}") |

## Failed Deployments

EOF

if [[ ${#FAILED_IDS[@]} -gt 0 ]]; then
    echo "The following deployments failed:" >> "$REPORT_FILE"
    for id in "${FAILED_IDS[@]}"; do
        echo "- $id" >> "$REPORT_FILE"
        log_error "Failed: $id (see $DEPLOY_LOG_DIR/$id.log)"
    done
else
    echo "None 🎉" >> "$REPORT_FILE"
fi

# Print summary
echo ""
log_info "=========================================="
log_info "Deployment Summary"
log_info "=========================================="
log_info "Total:     $COUNT"
log_info "Success:   $SUCCESS"
log_info "Failed:    $FAILED"
log_info "Success Rate: $(awk "BEGIN {printf \"%.1f%%\", ($SUCCESS/$COUNT)*100}")"
log_info "Report:    $REPORT_FILE"
log_info "=========================================="

# Exit with error if any deployment failed
if [[ $FAILED -gt 0 ]]; then
    log_error "Some deployments failed. Check logs in $DEPLOY_LOG_DIR"
    exit 1
fi

log_info "All deployments completed successfully!"
exit 0
