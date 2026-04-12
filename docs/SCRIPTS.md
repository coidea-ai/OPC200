# OPC200 运维脚本清单

> 所有脚本均经过设计，支持脚本化操作

---

## 一、初始化脚本 (scripts/setup/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `customer-init.sh` | 客户初始化 | 新客户接入时创建目录结构和配置 |
| `init-tailscale.sh` | Tailscale 控制面初始化 | 基础设施部署 |
| `init-gateway.sh` | Gateway 集群初始化 | 云端集群部署 |
| `init-monitoring.sh` | 监控平台初始化 | 监控体系部署 |

**示例:**
```bash
# 初始化本地客户
./scripts/setup/customer-init.sh -i OPC-001 -m on-premise -t tskey-auth-xxxx

# 初始化云端客户
./scripts/setup/customer-init.sh -i OPC-151 -m cloud -f feishu-token
```

---

## 二、部署脚本 (scripts/deploy/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `deploy-onprem.sh` | 本地客户部署 | 在客户服务器上部署 Gateway |
| `deploy-cloud.sh` | 云端客户部署 | 在 K8s 上部署 Gateway |
| `install-skills.sh` | Skills 安装/更新 | 安装或更新客户 Skills |
| `rolling-update.sh` | 滚动更新 | 批量更新所有客户 |

**示例:**
```bash
# 部署本地客户
./scripts/deploy/deploy-onprem.sh -i OPC-001

# 部署云端客户
./scripts/deploy/deploy-cloud.sh -i OPC-151 -f feishu-token

# 安装 Skills
./scripts/deploy/install-skills.sh --id OPC-001 --skill opc-journal

# 更新所有 Skills
./scripts/deploy/install-skills.sh --id OPC-001 --update

# 卸载 Skill
./scripts/deploy/install-skills.sh --id OPC-001 --skill opc-journal-core --uninstall
```

---

## 三、维护脚本 (scripts/maintenance/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `health-check.sh` | 健康检查 | 定期检查系统和客户健康状态 |
| `backup-manager.sh` | 备份管理 | 创建、恢复、清理备份 |
| `update-skills.sh` | Skills 批量更新 | 批量更新所有客户的 Skills |
| `rotate-logs.sh` | 日志轮转 | 自动轮转和清理日志 |
| `cleanup.sh` | 清理任务 | 清理临时文件和旧数据 |
| `offline-pack-sync.sh` | 离线包同步 | 同步离线知识包到本地客户 |

**示例:**
```bash
# 健康检查
./scripts/maintenance/health-check.sh -i OPC-001
./scripts/maintenance/health-check.sh -m all  # 检查所有

# 创建备份
./scripts/maintenance/backup-manager.sh --id OPC-001 backup

# 恢复备份
./scripts/maintenance/backup-manager.sh --id OPC-001 restore --name auto-20260321-120000

# 清理旧备份（保留3天）
./scripts/maintenance/backup-manager.sh --id OPC-001 cleanup --retention 3

# 列出备份
./scripts/maintenance/backup-manager.sh --id OPC-001 list
```

---

## 四、支持脚本 (scripts/support/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `vpn-manager.sh` | VPN 管理 | 连接客户节点、请求紧急访问 |
| `emergency-access.sh` | 紧急访问申请 | 申请临时访问权限 |
| `remote-session.sh` | 远程会话管理 | 管理远程协助会话 |
| `customer-communication.sh` | 客户通知 | 批量发送通知 |

**示例:**
```bash
# 查看节点状态
./scripts/support/vpn-manager.sh --id OPC-001 status

# 连接到客户节点
./scripts/support/vpn-manager.sh --id OPC-001 connect

# 请求紧急访问
./scripts/support/vpn-manager.sh --id OPC-001 emergency-access \
  --reason "Gateway故障恢复" --duration 2h

# 生成新的 auth key
./scripts/support/vpn-manager.sh --id OPC-001 generate-key

# 列出所有节点
./scripts/support/vpn-manager.sh list-nodes
```

---

## 五、恢复脚本 (scripts/recovery/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `emergency-recovery.sh` | 紧急恢复 | 自动恢复各种故障场景 |
| `data-vault-repair.sh` | 数据保险箱修复 | 修复损坏的数据保险箱 |
| `gateway-rebuild.sh` | Gateway 重建 | 完全重建 Gateway |
| `tailscale-reconnect.sh` | VPN 重连 | 恢复 Tailscale 连接 |

**示例:**
```bash
# Gateway 故障恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario gateway-failure

# 数据保险箱损坏恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario data-vault-corruption

# Tailscale 断开恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario tailscale-disconnect

# 磁盘满恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario disk-full

# 内存耗尽恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario memory-exhausted

# 模拟运行（不实际执行）
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario disk-full --dry-run
```

---

## 六、监控脚本 (scripts/monitoring/)

| 脚本 | 功能 | 使用场景 |
|------|------|---------|
| `metrics-collector.sh` | 指标采集 | 采集系统和业务指标 |
| `alert-generator.sh` | 告警生成 | 基于规则生成告警 |
| `report-generator.sh` | 报告生成 | 生成日报/周报/月报 |

---

## 脚本设计原则

### 1. 统一接口
所有脚本都支持:
```bash
-h, --help          # 显示帮助
-v, --verbose       # 详细输出
--dry-run           # 模拟运行
--id OPC-XXX        # 指定客户ID
```

### 2. 颜色输出
- 🔵 `[INFO]` - 信息
- 🟢 `[SUCCESS]` - 成功
- 🟡 `[WARN]` - 警告
- 🔴 `[ERROR]` - 错误

### 3. 审计日志
涉及客户数据的操作都会记录:
```
customers/on-premise/OPC-XXX/remote-sessions/
├── access-request-YYYYMMDD-HHMMSS.yml
├── emergency-recovery-YYYYMMDD-HHMMSS.log
└── session-recording-YYYYMMDD-HHMMSS.cast
```

### 4. 错误处理
- 所有脚本使用 `set -euo pipefail`
- 错误时返回非零退出码
- 提供清晰的错误信息

### 5. 幂等性
- 多次执行不会产生副作用
- 适合自动化和定时任务

---

## 常用工作流

### 工作流 1: 新客户接入
```bash
# 1. 初始化客户
./scripts/setup/customer-init.sh -i OPC-001 -m on-premise -t tskey-auth-xxxx

# 2. 部署 Gateway
ssh opc@customer-server ./deploy-onprem.sh -i OPC-001

# 3. 安装 Skills
./scripts/deploy/install-skills.sh --id OPC-001 --skill opc-journal

# 4. 健康检查
./scripts/maintenance/health-check.sh -i OPC-001

# 5. 创建初始备份
./scripts/maintenance/backup-manager.sh --id OPC-001 backup
```

### 工作流 2: 紧急故障响应
```bash
# 1. 检查状态
./scripts/maintenance/health-check.sh -i OPC-001

# 2. 连接到客户节点
./scripts/support/vpn-manager.sh --id OPC-001 connect

# 3. 执行恢复
./scripts/recovery/emergency-recovery.sh --id OPC-001 --scenario gateway-failure

# 4. 验证恢复
./scripts/maintenance/health-check.sh -i OPC-001
```

### 工作流 3: 定期维护
```bash
# 1. 健康检查所有客户
for id in $(cat customers/registry/master-index.yml | grep "^OPC-" | cut -d: -f1); do
    ./scripts/maintenance/health-check.sh -i $id
done

# 2. 创建备份
for id in OPC-{001..150}; do
    ./scripts/maintenance/backup-manager.sh --id $id backup --upload
done

# 3. 清理旧备份
for id in OPC-{001..150}; do
    ./scripts/maintenance/backup-manager.sh --id $id cleanup --retention 7
done

# 4. 更新 Skills
./scripts/maintenance/update-skills.sh --all --version latest
```

---

## 自动化集成

### Cron 任务示例
```bash
# /etc/cron.d/opc200-maintenance

# 每小时健康检查
0 * * * * root /opc200/scripts/maintenance/health-check.sh -m all

# 每天凌晨2点备份
0 2 * * * root /opc200/scripts/maintenance/backup-manager.sh --all backup

# 每周日清理旧备份
0 3 * * 0 root /opc200/scripts/maintenance/backup-manager.sh --all cleanup

# 每天日志轮转
0 4 * * * root /opc200/scripts/maintenance/rotate-logs.sh
```

### CI/CD 集成
```yaml
# .github/workflows/deploy.yml
- name: Deploy to Customer
  run: |
    ./scripts/deploy/deploy-onprem.sh -i ${{ matrix.customer-id }}
    ./scripts/deploy/install-skills.sh --id ${{ matrix.customer-id }} --skill opc-journal
    ./scripts/maintenance/health-check.sh -i ${{ matrix.customer-id }}
```

---

*脚本清单版本: 2026-03-21*
