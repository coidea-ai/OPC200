#!/bin/bash
#===============================================================================
# OPC200 Logging Library
# 用途: 为所有运维脚本提供统一的日志格式
# 使用方法: source /opc200/scripts/lib/logging.sh
#===============================================================================

# 检查是否已加载
if [[ -n "${_OPC200_LOGGING_LOADED:-}" ]]; then
    return 0
fi
_OPC200_LOGGING_LOADED=1

# 颜色定义
OPC_RED='\033[0;31m'
OPC_GREEN='\033[0;32m'
OPC_YELLOW='\033[1;33m'
OPC_BLUE='\033[0;34m'
OPC_GRAY='\033[0;90m'
OPC_NC='\033[0m' # No Color

# 日志级别
OPC_LOG_LEVEL=${OPC_LOG_LEVEL:-"INFO"}
OPC_LOG_LEVELS=("DEBUG" "INFO" "WARN" "ERROR")

# Dry run 模式
OPC_DRY_RUN=${OPC_DRY_RUN:-"false"}

# 获取当前时间戳
_opc_log_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# 检查日志级别是否允许输出
_opc_log_level_allowed() {
    local level="$1"
    local current_level_num=1
    local target_level_num=1
    
    for i in "${!OPC_LOG_LEVELS[@]}"; do
        if [[ "${OPC_LOG_LEVELS[$i]}" == "$OPC_LOG_LEVEL" ]]; then
            current_level_num=$i
        fi
        if [[ "${OPC_LOG_LEVELS[$i]}" == "$level" ]]; then
            target_level_num=$i
        fi
    done
    
    [[ $target_level_num -ge $current_level_num ]]
}

# 敏感信息脱敏
_opc_mask_sensitive() {
    local input="$1"
    # 脱敏常见的敏感模式
    echo "$input" | sed -E \
        -e 's/(key[=:])[a-zA-Z0-9_-]{8,}/\1***MASKED***/gi' \
        -e 's/(token[=:])[a-zA-Z0-9_-]{8,}/\1***MASKED***/gi' \
        -e 's/(secret[=:])[a-zA-Z0-9_-]{8,}/\1***MASKED***/gi' \
        -e 's/(password[=:])[a-zA-Z0-9_-]{8,}/\1***MASKED***/gi' \
        -e 's/(authkey[=:])[a-zA-Z0-9_-]{8,}/\1***MASKED***/gi' \
        2>/dev/null || echo "$input"
}

# 核心日志函数
_opc_log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(_opc_log_timestamp)
    local script_name=$(basename "${BASH_SOURCE[2]:-$0}")
    
    if ! _opc_log_level_allowed "$level"; then
        return 0
    fi
    
    # 脱敏敏感信息
    message=$(_opc_mask_sensitive "$message")
    
    # JSON 格式日志（如果启用结构化日志）
    if [[ "${OPC_JSON_LOG:-}" == "true" ]]; then
        printf '{"timestamp":"%s","level":"%s","script":"%s","message":"%s"}\n' \
            "$timestamp" "$level" "$script_name" "$message"
    else
        # 人类可读格式
        local color=""
        case "$level" in
            DEBUG) color=$OPC_GRAY ;;
            INFO)  color=$OPC_BLUE ;;
            WARN)  color=$OPC_YELLOW ;;
            ERROR) color=$OPC_RED ;;
        esac
        
        echo -e "${color}[${level}]${OPC_NC} ${OPC_GRAY}${timestamp}${OPC_NC} ${message}"
    fi
}

# 便捷函数
log_debug() { _opc_log "DEBUG" "$@"; }
log_info() { _opc_log "INFO" "$@"; }
log_warn() { _opc_log "WARN" "$@"; }
log_error() { _opc_log "ERROR" "$@"; }

log_success() {
    echo -e "${OPC_GREEN}[✓]${OPC_NC} $1"
}

log_failure() {
    echo -e "${OPC_RED}[✗]${OPC_NC} $1"
}

# Dry run 包装器
dry_run() {
    if [[ "$OPC_DRY_RUN" == "true" ]]; then
        log_warn "[DRY-RUN] Would execute: $*"
        return 0
    else
        "$@"
    fi
}

# 确认提示
confirm() {
    local message="${1:-Are you sure?}"
    local response
    
    read -p "$message (yes/no): " response
    [[ "$response" == "yes" ]]
}

# 解析通用参数
# 用法: parse_common_args "$@"
parse_common_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                export OPC_DRY_RUN="true"
                log_warn "Dry run mode enabled - no changes will be made"
                shift
                ;;
            --verbose|-v)
                export OPC_LOG_LEVEL="DEBUG"
                shift
                ;;
            --quiet|-q)
                export OPC_LOG_LEVEL="WARN"
                shift
                ;;
            --json-log)
                export OPC_JSON_LOG="true"
                shift
                ;;
            *)
                # 保留未知参数给调用者处理
                shift
                ;;
        esac
    done
}

# 测量执行时间
# 用法: timer_start; ...; timer_stop "Operation"
_timer_start_time=""
timer_start() {
    _timer_start_time=$(date +%s)
}

timer_stop() {
    local operation="${1:-Operation}"
    if [[ -n "$_timer_start_time" ]]; then
        local end_time=$(date +%s)
        local duration=$((end_time - _timer_start_time))
        log_info "$operation completed in ${duration}s"
        _timer_start_time=""
    fi
}

# 进度条
# 用法: progress_bar current total
progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %d%%" "$percentage"
}
