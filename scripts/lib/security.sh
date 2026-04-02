#!/bin/bash
#===============================================================================
# OPC200 Security Library
# 用途: 敏感信息处理和密钥管理
#===============================================================================

[[ -n "${_OPC200_SECURITY_LOADED:-}" ]] && return 0
_OPC200_SECURITY_LOADED=1

# Mask sensitive strings in output
opc_mask_secret() {
    local input="$1"
    local mask_char="${2:-***REDACTED***}"
    
    # Patterns to mask
    local patterns=(
        's/([a-zA-Z0-9_-]*key[=:])[a-zA-Z0-9_\-]+/\1'"$mask_char"'/gi'
        's/([a-zA-Z0-9_-]*token[=:])[a-zA-Z0-9_\-]+/\1'"$mask_char"'/gi'
        's/([a-zA-Z0-9_-]*secret[=:])[a-zA-Z0-9_\-]+/\1'"$mask_char"'/gi'
        's/([a-zA-Z0-9_-]*password[=:])[a-zA-Z0-9_\-]+/\1'"$mask_char"'/gi'
        's/(authkey[=:])[a-zA-Z0-9_\-]+/\1'"$mask_char"'/gi'
    )
    
    local output="$input"
    for pattern in "${patterns[@]}"; do
        output=$(echo "$output" | sed -E "$pattern" 2>/dev/null || echo "$output")
    done
    
    echo "$output"
}

# Check file permissions (should not be world-readable for secrets)
opc_check_file_permissions() {
    local file="$1"
    local max_perms="${2:-640}"  # Default: owner rw, group r, other none
    
    [[ -f "$file" ]] || return 1
    
    local actual_perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%Lp" "$file" 2>/dev/null)
    
    if [[ "$actual_perms" -gt "${max_perms##0}" ]]; then
        echo "WARNING: $file has permissions $actual_perms (should be <= $max_perms)"
        return 1
    fi
    
    return 0
}

# Secure file creation with proper permissions
opc_secure_create_file() {
    local file="$1"
    local perms="${2:-600}"
    
    # Create file with restricted permissions from the start
    (umask 077; touch "$file")
    chmod "$perms" "$file"
}

# Secure directory creation
opc_secure_create_dir() {
    local dir="$1"
    local perms="${2:-700}"
    
    mkdir -p "$dir"
    chmod "$perms" "$dir"
}

# Get secret from environment or file
opc_get_secret() {
    local var_name="$1"
    local file_path="$2"
    local default_value="${3:-}"
    
    # First try environment variable
    local env_var="OPC_${var_name^^}"
    if [[ -n "${!env_var:-}" ]]; then
        echo "${!env_var}"
        return 0
    fi
    
    # Then try file
    if [[ -f "$file_path" ]]; then
        if opc_check_file_permissions "$file_path" 600; then
            cat "$file_path"
            return 0
        else
            echo "ERROR: $file_path has insecure permissions" >&2
            return 1
        fi
    fi
    
    # Return default or fail
    if [[ -n "$default_value" ]]; then
        echo "$default_value"
        return 0
    fi
    
    return 1
}

# Validate that a string looks like a secure key
opc_is_valid_key() {
    local key="$1"
    local min_length="${2:-16}"
    
    # Check minimum length
    [[ ${#key} -ge $min_length ]] || return 1
    
    # Check it has some complexity (not just repeating chars)
    local unique_chars=$(echo "$key" | fold -w1 | sort -u | wc -l)
    [[ $unique_chars -ge 4 ]] || return 1
    
    return 0
}

# Audit logging for security events
opc_security_audit() {
    local event="$1"
    local details="${2:-}"
    local customer_id="${3:-system}"
    
    local audit_dir="${OPC_LOG_DIR:-/var/log/opc200}/security"
    mkdir -p "$audit_dir"
    
    local audit_file="${audit_dir}/audit-$(date +%Y%m).log"
    
    printf '[%s] [%s] customer=%s event="%s" %s\n' \
        "$(date -Iseconds)" \
        "${OPC_AUDIT_ID:-$(hostname)}" \
        "$customer_id" \
        "$event" \
        "$details" >> "$audit_file"
}
