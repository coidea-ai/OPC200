#!/bin/bash
# OPC200 夜间安全审计脚本
# 版本: 2026.1
# 基于 OpenClaw Security Practice Guide v2.8

set -uo pipefail

# 配置
REPORT_DIR="${HOME}/.openclaw/opc200/security-reports"
LOG_DIR="${HOME}/.openclaw/opc200/logs"
CONFIG_DIR="${HOME}/.openclaw/opc200/configs"
REPORT_FILE="${REPORT_DIR}/audit-$(date +%Y%m%d-%H%M%S).md"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 创建目录
mkdir -p "$REPORT_DIR" "$LOG_DIR"

# 轮换旧报告（保留30天）
find "$REPORT_DIR" -name "audit-*.md" -mtime +30 -delete 2>/dev/null

# 计数器
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# 初始化报告
cat > "$REPORT_FILE" <> EOF
# OPC200 夜间安全审计报告

**生成时间**: $(date -Iseconds)  
**主机**: $(hostname)  
**租户ID**: ${OPC200_TENANT_ID:-unknown}

---

## 检查汇总

| 状态 | 数量 |
|------|------|
| ✅ 通过 | PENDING |
| ⚠️  警告 | PENDING |
| ❌ 失败 | PENDING |

---

EOF

echo "🔍 开始安全审计..."
echo ""

# 辅助函数
log_pass() {
    echo -e "${GREEN}✅${NC} $1"
    echo "✅ $1" >> "$REPORT_FILE"
    ((CHECKS_PASSED++))
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
    echo "⚠️  $1" >> "$REPORT_FILE"
    ((CHECKS_WARNING++))
}

log_fail() {
    echo -e "${RED}❌${NC} $1"
    echo "❌ $1" >> "$REPORT_FILE"
    ((CHECKS_FAILED++))
}

log_section() {
    echo ""
    echo -e "${GREEN}$1${NC}"
    echo "" >> "$REPORT_FILE"
    echo "## $1" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

# ========== 检查 1: Gateway 网络暴露 ==========
log_section "1. Gateway 网络暴露检查"

if command -v openclaw &> /dev/null; then
    GATEWAY_BIND=$(openclaw config get gateway.bind 2>/dev/null || echo "unknown")
    
    if [[ "$GATEWAY_BIND" == "loopback" || "$GATEWAY_BIND" == "tailnet" ]]; then
        log_pass "Gateway 绑定安全: $GATEWAY_BIND"
    elif [[ "$GATEWAY_BIND" == "127.0.0.1" || "$GATEWAY_BIND" == "localhost" ]]; then
        log_pass "Gateway 绑定本地: $GATEWAY_BIND"
    else
        log_fail "Gateway 绑定风险: $GATEWAY_BIND (应为 loopback 或 tailnet)"
    fi
else
    log_warn "无法检查 Gateway 配置 (openclaw 命令未找到)"
fi

# 检查端口暴露
if command -v netstat &> /dev/null; then
    PUBLIC_BIND=$(netstat -tlnp 2>/dev/null | grep ":18789" | grep -v "127.0.0.1" | grep -v "::1" || true)
    if [[ -z "$PUBLIC_BIND" ]]; then
        log_pass "端口 18789 未暴露在公网"
    else
        log_fail "端口 18789 暴露在公网: $PUBLIC_BIND"
    fi
elif command -v ss &> /dev/null; then
    PUBLIC_BIND=$(ss -tlnp 2>/dev/null | grep ":18789" | grep -v "127.0.0.1" | grep -v "::1" || true)
    if [[ -z "$PUBLIC_BIND" ]]; then
        log_pass "端口 18789 未暴露在公网"
    else
        log_fail "端口 18789 暴露在公网: $PUBLIC_BIND"
    fi
fi

# ========== 检查 2: Agent-Blind 凭据 ==========
log_section "2. Agent-Blind 凭据检查"

if [[ -f "$CONFIG_DIR/gateway-secure.yml" ]]; then
    if grep -q "credential_mode:.*agent-blind" "$CONFIG_DIR/gateway-secure.yml" 2>/dev/null; then
        log_pass "Agent-Blind 凭据模式已配置"
    else
        log_warn "未检测到 Agent-Blind 凭据配置"
    fi
else
    log_warn "未找到配置文件"
fi

# 检查明文凭据存储
PLAIN_CREDENTIALS=$(find ~/.openclaw -name "*auth*" -o -name "*credential*" -o -name "*secret*" 2>/dev/null | head -10)
if [[ -n "$PLAIN_CREDENTIALS" ]]; then
    log_warn "发现潜在明文凭据文件: $(echo "$PLAIN_CREDENTIALS" | wc -l) 个"
    echo "文件列表:" >> "$REPORT_FILE"
    echo "$PLAIN_CREDENTIALS" | sed 's/^/  - /' >> "$REPORT_FILE"
else
    log_pass "未发现明文凭据文件"
fi

# ========== 检查 3: Token 轮换 ==========
log_section "3. Token 轮换状态"

if [[ -f ~/.openclaw/config.json ]]; then
    TOKEN_AGE_DAYS=$(( ($(date +%s) - $(stat -c %Y ~/.openclaw/config.json 2>/dev/null || echo 0)) / 86400 ))
    
    if [[ $TOKEN_AGE_DAYS -lt 30 ]]; then
        log_pass "配置/Token 年龄正常: ${TOKEN_AGE_DAYS} 天"
    elif [[ $TOKEN_AGE_DAYS -lt 60 ]]; then
        log_warn "Token 建议轮换: ${TOKEN_AGE_DAYS} 天"
    else
        log_fail "Token 需要立即轮换: ${TOKEN_AGE_DAYS} 天"
    fi
else
    log_warn "未找到 OpenClaw 配置文件"
fi

# ========== 检查 4: Skill 安全 ==========
log_section "4. Skill 安全审计"

SKILLS_DIR="${HOME}/.openclaw/skills"
if [[ -d "$SKILLS_DIR" ]]; then
    SKILL_COUNT=$(find "$SKILLS_DIR" -maxdepth 1 -type d | wc -l)
    log_pass "已安装 Skills: $((SKILL_COUNT - 1)) 个"
    
    # 检查可疑 Skills
    SUSPICIOUS=$(find "$SKILLS_DIR" -name "*.sh" -o -name "*eval*" -o -name "*exec*" 2>/dev/null || true)
    if [[ -n "$SUSPICIOUS" ]]; then
        log_warn "发现潜在高风险文件，建议人工审查"
    fi
else
    log_warn "未找到 Skills 目录"
fi

# ========== 检查 5: 沙箱模式 ==========
log_section "5. 沙箱模式检查"

if [[ -f "$CONFIG_DIR/gateway-secure.yml" ]]; then
    if grep -q "sandbox:.*true" "$CONFIG_DIR/gateway-secure.yml" 2>/dev/null; then
        log_pass "沙箱模式已启用"
    else
        log_warn "沙箱模式未明确启用"
    fi
fi

# ========== 检查 6: 审计日志 ==========
log_section "6. 审计日志检查"

if [[ -d "$LOG_DIR" ]]; then
    RECENT_LOGS=$(find "$LOG_DIR" -name "*.log" -mtime -7 2>/dev/null | wc -l)
    if [[ $RECENT_LOGS -gt 0 ]]; then
        log_pass "审计日志活跃: ${RECENT_LOGS} 个日志文件"
    else
        log_warn "最近 7 天无审计日志"
    fi
else
    log_warn "未找到日志目录"
fi

# ========== 检查 7: 文件权限 ==========
log_section "7. 文件权限检查"

CONFIG_PERMS=$(stat -c "%a" ~/.openclaw/config.json 2>/dev/null || echo "unknown")
if [[ "$CONFIG_PERMS" == "600" || "$CONFIG_PERMS" == "644" ]]; then
    log_pass "配置文件权限正确: $CONFIG_PERMS"
else
    log_warn "配置文件权限可能需要调整: $CONFIG_PERMS (建议 600)"
fi

# ========== 检查 8: Tailscale 状态 ==========
log_section "8. Tailscale VPN 检查"

if command -v tailscale &> /dev/null; then
    if tailscale status &> /dev/null; then
        log_pass "Tailscale 连接正常"
        
        # 检查是否使用 tailnet
        if tailscale status | grep -q "tag:opc"; then
            log_pass "节点标签正确 (tag:opc)"
        fi
    else
        log_fail "Tailscale 未连接"
    fi
else
    log_warn "Tailscale 未安装"
fi

# ========== 生成报告汇总 ==========
echo ""
echo "---"
echo ""

# 更新报告汇总
cat >> "$REPORT_FILE" <> EOF

---

## 详细建议

### 立即行动 (失败项)
$(if [[ $CHECKS_FAILED -gt 0 ]]; then echo "- 修复上述失败的安全检查项"; else echo "- 无立即行动项"; fi)

### 近期关注 (警告项)
$(if [[ $CHECKS_WARNING -gt 0 ]]; then echo "- 处理上述警告项，提升安全态势"; else echo "- 无近期关注项"; fi)

### 安全建议
1. 定期审查已安装的 Skills
2. 保持 OpenClaw 和 Skills 更新
3. 定期轮换访问令牌
4. 审查审计日志中的异常活动
5. 进行定期的安全演练

---

*报告生成: $(date -Iseconds)*  
*OPC200 Security Audit v2026.1*
EOF

# 更新汇总表格
sed -i "s/PENDING/$(printf '| ✅ 通过 | %d |\n| ⚠️  警告 | %d |\n| ❌ 失败 | %d |' $CHECKS_PASSED $CHECKS_WARNING $CHECKS_FAILED)/" "$REPORT_FILE"

# 输出汇总
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           审计完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 通过: $CHECKS_PASSED${NC}"
echo -e "${YELLOW}⚠️  警告: $CHECKS_WARNING${NC}"
echo -e "${RED}❌ 失败: $CHECKS_FAILED${NC}"
echo ""
echo "📄 完整报告: $REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 发送告警（如果有失败项）
if [[ $CHECKS_FAILED -gt 0 ]]; then
    echo "🚨 发现 $CHECKS_FAILED 个安全问题，请立即查看报告！"
    # 可以在这里添加 webhook 通知
    exit 1
fi

exit 0
