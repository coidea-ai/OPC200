# OPC200 安全指南

> **版本**: 2.2.0  
> **安全等级**: Tier 3 - Enterprise  
> **最后更新**: 2026-03-24

## 目录

1. [安全架构](#安全架构)
2. [数据分级](#数据分级)
3. [Agent-Blind Credentials](#agent-blind-credentials)
4. [部署安全](#部署安全)
5. [运维安全](#运维安全)
6. [合规](#合规)
7. [事件响应](#事件响应)

---

## 安全架构

### 三层防御

```
┌─────────────────────────────────────────┐
│           Layer 1: 访问控制             │
│  • 身份认证 (Token/OAuth)               │
│  • 网络隔离 (Tailscale VPN)             │
│  • 权限最小化                           │
├─────────────────────────────────────────┤
│           Layer 2: 数据保护             │
│  • 传输加密 (TLS 1.3)                   │
│  • 静态加密 (AES-256-GCM)               │
│  • 数据保险箱 (Agent-Blind)             │
├─────────────────────────────────────────┤
│           Layer 3: 审计监控             │
│  • 访问日志                             │
│  • 异常检测                             │
│  • 实时告警                             │
└─────────────────────────────────────────┘
```

### 信任模型

- **单个信任边界**: 每个客户环境是独立的信任边界
- **最小权限**: 任何组件只拥有完成任务所需的最小权限
- **零信任网络**: 即使在内网也进行身份验证

---

## 数据分级

### Tier 1: 关键数据（绝不上云）

| 数据类型 | 示例 | 存储 | 加密 |
|---------|------|------|------|
| 原始客户数据 | 客户业务数据 | 本地 | AES-256 |
| 专有代码 | 源代码、算法 | 本地 | AES-256 |
| 财务记录 | 收入、成本 | 本地 | AES-256 |

```bash
# Tier 1 存储路径
/data/vault/local-only/
├── sensitive-memory/
├── private-codebases/
└── customer-data/
```

### Tier 2: 敏感数据（脱敏后可同步）

| 数据类型 | 脱敏方式 | 存储 |
|---------|---------|------|
| 使用模式 | 匿名化 | 加密后同步 |
| 错误日志 | 脱敏处理 | 加密后同步 |
| 性能指标 | 聚合 | 加密后同步 |

### Tier 3: 公开数据

- 知识文章
- 最佳实践
- 公开文档

---

## Agent-Blind Credentials

### 核心概念

Agent **永远无法直接访问**凭证值，只能通过以下方式操作：

```python
# ✅ Agent 可以做的
vault.store_credential(
    name="api_key",
    credential_type="api_key",
    value="sk-...",  # 立即加密，Agent 看不到
    metadata={"service": "openai"}  # Agent 可以看到元数据
)

# 获取元数据（Agent 可见）
metadata = vault.get_credential_metadata(cred_id)
# 返回: {"name": "api_key", "type": "api_key", "metadata": {...}}

# ❌ Agent 不能直接做的
value = vault._credentials[cred_id].value  # 加密存储，无法直接访问
```

### 服务层解密

只有授权的服务可以解密：

```python
# 服务层（需要服务授权令牌）
value = vault.decrypt_for_service(
    credential_id="cred-123",
    service_auth_token="${SERVICE_TOKEN}"
)
```

### 凭证轮换

```bash
# 1. 生成新凭证
NEW_KEY=$(openssl rand -hex 32)

# 2. 轮换
./scripts/security/rotate-credential.sh \
  --id cred-123 \
  --new-value "${NEW_KEY}"

# 3. 验证
./scripts/security/verify-credential.sh --id cred-123
```

---

## 部署安全

### 本地部署

```yaml
# 安全清单
deployment:
  # ✅ 绑定到 loopback
  gateway_bind: "127.0.0.1:18789"
  
  # ✅ 使用 Tailscale VPN
  vpn_enabled: true
  vpn_type: "tailscale"
  
  # ✅ 数据保险箱
  vault_enabled: true
  vault_encryption: "aes-256-gcm"
  
  # ✅ 只读容器
  container_read_only: true
  container_no_new_privs: true
```

### 云端部署

```yaml
# 额外安全措施
cloud_security:
  # TLS 终止
  tls_termination: "ingress"
  cert_manager: "letsencrypt"
  
  # WAF
  waf_enabled: true
  waf_rules: "owasp-top-10"
  
  # 网络策略
  network_policies: true
  pod_security_policy: "restricted"
```

### 容器安全

```dockerfile
# Dockerfile 安全实践
FROM python:3.11-slim

# 创建非 root 用户
RUN groupadd -r opc200 && useradd -r -g opc200 opc200

# 最小权限
USER opc200

# 只读根文件系统
read_only: true

# 限制资源
memory_limit: "512m"
cpu_limit: "0.5"
```

---

## 运维安全

### 访问控制

```bash
# SSH 仅通过 Tailscale
tailscale ssh opc-001

# 禁止直接 SSH
ufw deny 22/tcp
```

### 审计日志

```bash
# 查看访问日志
tail -f /var/log/opc200/audit.log

# 分析异常访问
./scripts/security/audit-analyzer.sh \
  --since "24h" \
  --severity high
```

### 紧急访问（Break-glass）

```bash
# 1. 客户授权
# 客户通过飞书/邮件确认

# 2. 生成临时访问密钥
./scripts/support/emergency-access.sh \
  --customer OPC-001 \
  --reason "Gateway故障恢复" \
  --duration 2h \
  --requester "support@coidea.ai"

# 3. 访问并修复
# 所有操作被记录

# 4. 撤销访问
./scripts/support/emergency-access.sh \
  --customer OPC-001 \
  --revoke
```

---

## 合规

### 数据驻留

```yaml
# 配置数据驻留
compliance:
  data_residency:
    enabled: true
    region: "cn"  # cn / eu / us
    
  # 确保数据不离开指定区域
  cross_border_transfer: false
```

### GDPR / CCPA

```yaml
# 用户权利
user_rights:
  # 数据导出
  data_export:
    enabled: true
    formats: ["json", "csv"]
    max_wait_hours: 48
  
  # 数据删除
  right_to_deletion:
    enabled: true
    grace_period_days: 30
    verification_required: true
```

### 审计合规

```bash
# 生成合规报告
./scripts/security/compliance-report.sh \
  --period "2026-Q1" \
  --format pdf \
  --output /reports/compliance-q1.pdf
```

---

## 事件响应

### 安全事件分级

| 级别 | 描述 | 响应时间 | 示例 |
|-----|------|---------|------|
| P0 | 关键 | 15分钟 | 数据泄露、服务中断 |
| P1 | 严重 | 1小时 | 未授权访问、凭证泄露 |
| P2 | 中等 | 4小时 | 异常流量、配置错误 |
| P3 | 低 | 24小时 | 日志异常、轻微告警 |

### 响应流程

```
检测 ──► 确认 ──► 遏制 ──► 根除 ──► 恢复 ──► 复盘
  │       │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼       ▼
告警    评估    隔离    修复    验证    文档
```

### 响应脚本

```bash
# 立即隔离受影响的客户
./scripts/security/isolate-customer.sh --id OPC-XXX

# 轮换所有凭证
./scripts/security/emergency-rotation.sh --customer OPC-XXX

# 生成事件报告
./scripts/security/incident-report.sh \
  --incident INC-2026-001 \
  --output /incidents/INC-2026-001.pdf
```

---

## 安全资源

- [安全更新订阅](mailto:security@coidea.ai)
- [漏洞报告](https://security.opc200.coidea.ai)
- [安全公告](https://docs.opc200.coidea.ai/security)

## 参考

- [SYSTEM.md](../SYSTEM.md) - 架构设计
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 部署指南
- [OpenClaw Security Docs](https://docs.openclaw.ai/gateway/security)
