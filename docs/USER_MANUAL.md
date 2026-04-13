# OPC200 - 用户手册

## 目录

1. [快速开始](#快速开始)
2. [核心功能](#核心功能)
3. [使用指南](#使用指南)
4. [故障排除](#故障排除)
5. [常见问题](#常见问题)

## 快速开始

### 系统要求

- **操作系统**: Linux (Ubuntu 22.04+ / Debian 12+)
- **CPU**: 4+ 核心
- **内存**: 8GB+ (推荐 16GB)
- **存储**: 100GB+ SSD
- **网络**: 可访问 Tailscale 控制平面

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/coidea-ai/OPC200.git
   cd OPC200
   ```

2. **初始化客户环境**
   ```bash
   ./scripts/setup/customer-init.sh -i OPC-001 -m on-premise -t tskey-auth-xxxx
   ```

3. **部署 Gateway**
   ```bash
   ./scripts/deploy/deploy-onprem.sh -i OPC-001
   ```

4. **安装 Skills**
   ```bash
   ./scripts/deploy/install-skills.sh --id OPC-001 --skill opc-journal
   ```

## 核心功能

### 1. 日志记录 (Journal)

记录您的创业旅程：

```
用户: "今天完成了产品原型，但是有点担心技术选型"

系统自动:
- 创建日志条目 JE-20260321-001
- 链接到之前的技术讨论 JE-20260318-003
- 标记情绪状态: "anxious_but_accomplished"
- 创建技术验证的后续任务
```

### 2. 模式识别 (Pattern Recognition)

每周自动分析：

```
📊 本周模式分析

工作节奏:
• 高效时段: 周三下午、周五上午
• 低谷时段: 周一早晨
• 平均专注时长: 2.3 小时

决策模式:
• 风险偏好: 保守型
• 常见犹豫点: 技术选型、定价策略
• 求助时机: 通常在问题出现 2 天后

建议:
"尝试将重要决策安排在周三下午"
"考虑提前 1 天寻求技术建议"
```

### 3. 里程碑追踪 (Milestone Tracker)

自动检测重要时刻：

```
🎉 里程碑达成: 首次产品发布

Day: 45
Time: 2026-03-21 14:30
Context: 独立完成从想法到上线的完整流程

Previous milestone: 完成 MVP (Day 28)
Next predicted: 首笔销售 (预计 Day 52)
```

### 4. 异步任务 (Async Tasks)

后台执行长时间任务：

```
用户: "我需要一份竞品分析报告，明天早上要"

Bot: "收到！已创建异步任务 #RESEARCH-007
     分配给 Research Agent
     预计完成: 明早 8:00
     完成后将发送飞书通知并生成摘要"

[Next morning]
Bot: "☀️ #RESEARCH-007 完成！
     发现 3 个关键洞察，已同步到您的 Journal"
```

## 使用指南

### 日常交互

| 时段 | 模式 | 典型交互 |
|------|------|---------|
| 06-09 | 温和启动 | 隔夜任务更新、今日优先事项 |
| 09-12 | 高效执行 | 深度工作支持、Agent 优先 |
| 12-14 | 轻松交流 | 行业资讯、轻松问答 |
| 14-18 | 协作模式 | 多 Agent 协作、复杂任务 |
| 18-22 | 反思总结 | Journal 摘要、明日预备 |
| 22-06 | 静默守护 | 后台任务执行、紧急监控 |

### 常用命令

```bash
# 健康检查
./scripts/maintenance/health-check.sh -i OPC-001

# 创建备份
./scripts/maintenance/backup-manager.sh --id OPC-001 backup

# 恢复备份
./scripts/maintenance/backup-manager.sh --id OPC-001 restore --name auto-20260321-120000

# 查看日志
docker logs opc200-gateway

# 重启服务
docker compose restart
```

## 故障排除

### Gateway 无法启动

**症状**: Gateway 容器反复重启

**解决步骤**:
1. 检查日志: `docker logs opc200-gateway`
2. 验证配置: `cat customers/on-premise/OPC-001/deployment/gateway.yml`
3. 检查端口占用: `netstat -tlnp | grep 18789`
4. 重新部署: `./scripts/deploy/deploy-onprem.sh -i OPC-001`

### Tailscale 连接失败

**症状**: VPN 无法连接，显示 "not logged in"

**解决步骤**:
1. 检查状态: `tailscale status`
2. 重新认证: `tailscale up --auth-key $(cat customers/on-premise/OPC-001/tailscale/auth-key)`
3. 检查 ACL: 在 Tailscale 控制台验证标签配置

### Skills 未响应

**症状**: 技能命令无响应

**解决步骤**:
1. 检查安装状态: `ls -la /opt/opc200/OPC-001/skills/`
2. 重新安装: `./scripts/deploy/install-skills.sh -i OPC-001 --update`
3. 重启 Gateway: `docker restart opc200-gateway`

## 常见问题

**Q: 数据存储在哪里？**
A: 本地部署模式下，所有数据存储在客户本地：
   - 日志数据: `/opt/opc200/OPC-001/data/journal/`
   - 加密文件: `/opt/opc200/OPC-001/data-vault/encrypted/`
   - 配置: `/opt/opc200/OPC-001/deployment/`

**Q: 如何备份我的数据？**
A: 使用备份脚本：
   ```bash
   ./scripts/maintenance/backup-manager.sh --id OPC-001 backup
   ```
   备份默认保存在 `/opt/opc200/OPC-001/backup/`

**Q: 紧急情况下如何获得支持？**
A: 
1. 通过飞书联系支持团队
2. 支持工程师会申请紧急访问权限
3. 您在飞书中授权后，工程师可通过 VPN 接入
4. 所有操作都会被审计记录

**Q: 我可以导出我的数据吗？**
A: 可以，使用以下命令：
   ```bash
   # 导出为 JSON
   curl -H "Authorization: Bearer $TOKEN" \
        http://localhost:8080/api/v1/journal/export
   ```

**Q: 系统更新会影响我的数据吗？**
A: 不会。更新前会自动创建备份，且您的数据与应用程序代码分离存储。

---

更多帮助: support@coidea.ai
