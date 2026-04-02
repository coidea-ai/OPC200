#!/bin/bash
#===============================================================================
# OPC200 Configuration Library
# 用途: 统一加载和管理配置
# 使用方法: source /opc200/scripts/lib/config.sh
#===============================================================================

# Prevent double loading
[[ -n "${_OPC200_CONFIG_LOADED:-}" ]] && return 0
_OPC200_CONFIG_LOADED=1

# Default configuration values
_OPC_DEFAULTS=(
    "OPC_BASE_DIR:/opt/opc200"
    "OPC_DATA_DIR:/data/opc200"
    "OPC_LOG_DIR:/var/log/opc200"
    "OPC_BACKUP_RETENTION_DAYS:7"
    "OPC_LOG_LEVEL:INFO"
    "OPC_MAX_PARALLEL_CHECKS:10"
    "OPC_HEALTH_CHECK_TIMEOUT:30"
    "OPC_BACKUP_ENCRYPT:true"
    "OPC_DRY_RUN:false"
    "OPC_JSON_LOG:false"
)

# Configuration file search paths (in order of priority)
_OPC_CONFIG_PATHS=(
    "${PWD}/.opcrc"
    "${PWD}/opc.conf"
    "${HOME}/.config/opc/opcrc"
    "${HOME}/.opcrc"
    "/etc/opc/opcrc"
    "/opt/opc200/.opcrc"
)

# Load configuration from file
_opc_load_config_file() {
    local config_file="$1"
    
    [[ -f "$config_file" ]] || return 1
    
    # Source the config file
    # shellcheck source=/dev/null
    source "$config_file"
    
    return 0
}

# Find and load first available config file
opc_load_config() {
    local explicit_config="${1:-}"
    
    # If explicit config file provided, try to load it
    if [[ -n "$explicit_config" ]]; then
        if _opc_load_config_file "$explicit_config"; then
            return 0
        else
            echo "Error: Cannot load config file: $explicit_config" >&2
            return 1
        fi
    fi
    
    # Search for config file in standard paths
    for path in "${_OPC_CONFIG_PATHS[@]}"; do
        if _opc_load_config_file "$path"; then
            [[ "${OPC_DEBUG:-false}" == "true" ]] && echo "Loaded config from: $path" >&2
            return 0
        fi
    done
    
    # No config file found, use defaults
    return 0
}

# Apply default values for unset variables
opc_apply_defaults() {
    for default in "${_OPC_DEFAULTS[@]}"; do
        local key="${default%%:*}"
        local value="${default#*:}"
        
        if [[ -z "${!key:-}" ]]; then
            # Variable is not set, apply default
            export "$key=$value"
        fi
    done
}

# Get customer-specific paths
opc_get_customer_dir() {
    local customer_id="$1"
    local dir_type="${2:-base}"  # base, data, backup, config, logs
    
    case "$dir_type" in
        base)
            echo "${OPC_BASE_DIR}/${customer_id}"
            ;;
        data)
            echo "${OPC_DATA_DIR}/${customer_id}"
            ;;
        backup)
            echo "${OPC_BASE_DIR}/${customer_id}/backup"
            ;;
        config)
            echo "${OPC_BASE_DIR}/${customer_id}/config"
            ;;
        logs)
            echo "${OPC_LOG_DIR}/${customer_id}"
            ;;
        vault)
            echo "${OPC_BASE_DIR}/${customer_id}/data-vault"
            ;;
        *)
            echo "${OPC_BASE_DIR}/${customer_id}"
            ;;
    esac
}

# Validate customer ID format
opc_validate_customer_id() {
    local customer_id="$1"
    
    # Support formats: OPC-001, OPC-123, opc-001, etc.
    if [[ "$customer_id" =~ ^[Oo][Pp][Cc]-[0-9]{1,3}$ ]]; then
        return 0
    fi
    
    # Also support numeric format (1, 2, 123)
    if [[ "$customer_id" =~ ^[0-9]+$ ]]; then
        return 0
    fi
    
    return 1
}

# Parse customer ID to numeric form
opc_parse_customer_id() {
    local customer_id="$1"
    
    if [[ "$customer_id" =~ ^[0-9]+$ ]]; then
        echo "$customer_id"
    elif [[ "$customer_id" =~ ^[Oo][Pp][Cc]-([0-9]+)$ ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# Format customer ID to standard form
opc_format_customer_id() {
    local customer_id="$1"
    local num=$(opc_parse_customer_id "$customer_id")
    
    if [[ -n "$num" ]]; then
        printf "OPC-%03d" "$num"
    else
        echo ""
    fi
}

# Show current configuration
opc_show_config() {
    echo "OPC200 Configuration:"
    echo "===================="
    for default in "${_OPC_DEFAULTS[@]}"; do
        local key="${default%%:*}"
        echo "  $key=${!key}"
    done
}

# Initialize configuration (call this in scripts)
opc_init_config() {
    local explicit_config="${1:-}"
    
    # Load config file
    opc_load_config "$explicit_config"
    
    # Apply defaults for unset variables
    opc_apply_defaults
    
    # Export all config variables
    for default in "${_OPC_DEFAULTS[@]}"; do
        local key="${default%%:*}"
        export "$key"
    done
}
