# OPC200 - One Person Company 超级智能体支持平台

> **200 个一人公司，100 天 7×24 小时超级智能体陪伴式成长**

[![Version](https://img.shields.io/badge/version-2.4--refactoring-blue.svg)](./VERSION)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.4+-green.svg)](https://openclaw.ai)
[![Security](https://img.shields.io/badge/security-Data%20Vault%20Architecture-red.svg)](./SYSTEM.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

> **🚨 v2.4 重构中**: 基于 OpenClaw v2026.4.9 平台的记忆层升级，OPC200 正在进行战略转身。详见 [`CRITICAL_ANALYSIS_2026-04-10.md`](./CRITICAL_ANALYSIS_2026-04-10.md) 和 [`REFACTOR_PLAN.md`](./REFACTOR_PLAN.md)。

---

## 🎯 项目概述

OPC200 是一个面向 **One Person Company（一人公司）** 的 AI 智能体支持基础设施，通过 OpenClaw 平台提供持续 100 天的陪伴式成长服务。

### 核心能力

| 能力 | 说明 |
|------|------|
| **🤖 7×24 智能体陪伴** | 不只是问答，是连续 100 天的成长记录与回顾 |
| **📝 User Journal** | 100 天旅程的特定里程碑模型和数据契约 |
| **🔒 数据主权** | 本地数据保险箱，敏感信息绝不上云 |
| **🌐 混合部署** | 20 本地部署 + 180 云端托管 |
| **🛠️ 专属 Skills** | OPC Journal Suite（3 个核心差异化技能）|

---

## 🏗️ 架构设计

### 部署架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OPC200 部署分布 (200客户)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   本地部署 (20)                           云端托管 (180)                 │
│   ┌────────────────────────┐              ┌────────────────────────┐   │
│   │ • Tailscale VPN 连接   │              │ • 多租户共享基础设施   │   │
│   │ • 敏感数据本地存储     │              │ • Gateway-per-tenant   │   │
│   │ • All-in-One 容器      │              │ • S3/B2 自动备份       │   │
│   │ • 紧急远程访问授权     │              │                        │   │
│   └────────────────────────┘              └────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                    支持中心 (Support Hub)                    │      │
│   │  • 统一调度引擎  • 分级知识库  • 统一监控  • 应急响应中心     │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 技术栈

- **AI 平台**: [OpenClaw](https://openclaw.ai) Gateway
- **安全网络**: Tailscale VPN (WireGuard)
- **记忆存储**: SQLite + Qdrant 向量数据库
- **技能生态**: [ClawHub](https://clawhub.ai)
- **监控告警**: Prometheus + Grafana
- **运维自动化**: Bash/Python + Cron

---

## 📁 项目结构

```
opc200/
│
├── README.md                    # 本文件
├── SYSTEM.md                    # 架构方案文档（核心）
├── KNOWLEDGE_BASE.md            # 知识库与最佳实践
├── STRUCTURE.md                 # 项目文件结构
├── LICENSE                      # MIT 许可证
│
├── skills/                      # OpenClaw Skills（可发布到 ClawHub）
│   └── opc-journal/             # OPC Journal（单一 CLI Skill）
│       ├── SKILL.md             # Skill 文档
│       ├── scripts/             # 命令实现（init, record, analyze...）
│       ├── tests/               # 36 个测试
│       └── config.yml           # Skill 配置
│
├── opc-remi-lite/             # ⚠️ 已废弃 (DEPRECATED)
│
├── scripts/                     # 运维脚本
│   ├── setup/                   # 初始化脚本
│   │   └── customer-init.sh     # 客户初始化
│   ├── deploy/                  # 部署脚本
│   │   ├── deploy-onprem.sh     # 本地部署
│   │   ├── deploy-cloud.sh      # 云端部署
│   │   └── install-skills.sh    # Skills 安装
│   ├── maintenance/             # 维护脚本
│   │   ├── health-check.sh      # 健康检查
│   │   └── backup-manager.sh    # 备份管理
│   ├── support/                 # 支持脚本
│   │   └── vpn-manager.sh       # VPN 管理
│   └── recovery/                # 恢复脚本
│       └── emergency-recovery.sh # 紧急恢复
│
├── docs/                        # 文档
│   ├── SCRIPTS.md               # 脚本使用手册
│   ├── DEPLOYMENT.md            # 部署指南
│   ├── DEVELOPMENT.md           # 开发指南
│   └── SECURITY.md              # 安全指南
│
├── docker-compose.yml           # 开发环境编排
├── docker-compose.cloud.yml     # 云端多租户编排
├── docker-compose.onprem.yml    # 本地简化编排
└── Dockerfile.allinone          # 本地 All-in-One 镜像

> 重构相关文档:
> - [`CRITICAL_ANALYSIS_2026-04-10.md`](./CRITICAL_ANALYSIS_2026-04-10.md) — 现状批判分析
> - [`REFACTOR_PLAN.md`](./REFACTOR_PLAN.md) — 重构执行计划
```

---

## 🚀 快速开始

### 🎯 5 分钟体验（终端用户）

作为一人公司创业者，这是你第一天使用 OPC200：

```bash
# 1. 安装 OpenClaw（如果还没有）
npm install -g openclaw

# 2. 安装 OPC Journal
clawhub install coidea/opc-journal

# 3. 初始化你的 100 天旅程
openclaw run "opc-journal init --day 1 --goals '完成产品原型,获得首个付费用户'"

# 4. 开始记录（自然语言即可）
openclaw chat "今天完成了用户注册功能，但数据库选型有点纠结"
# 系统自动：创建日志条目 + 标记情绪状态 + 检测里程碑

# 5. 查看成长轨迹（第 7 天示例）
openclaw run "opc-journal insights --day 7"
# 输出：本周模式分析 + 里程碑检测 + 下周建议
```

### 方式一：本地部署（推荐数据敏感型客户）

```bash
# 1. 克隆仓库
git clone https://github.com/coidea-ai/OPC200.git
cd OPC200

# 2. 初始化客户（以 OPC-001 为例）
./scripts/setup/customer-init.sh \
  -i OPC-001 \
  -m on-premise \
  -t tskey-auth-xxxxxxxxxxxx

# 3. 部署 Gateway
./scripts/deploy/deploy-onprem.sh -i OPC-001

# 4. 安装 OPC Journal
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --skill opc-journal

# 5. 健康检查
./scripts/maintenance/health-check.sh -i OPC-001
```

### 方式二：云端托管（开箱即用）

```bash
# 1. 初始化云端客户
./scripts/setup/customer-init.sh \
  -i OPC-151 \
  -m cloud \
  -f feishu-bot-token

# 2. 部署到 K8s
./scripts/deploy/deploy-cloud.sh -i OPC-151

# 3. 安装 Skills
./scripts/deploy/install-skills.sh \
  --id OPC-151 \
  --skill opc-journal
```

---

## 💡 典型用户旅程

### Day 1: 产品启动
```
你："今天终于把想法落地了，做了个MVP，但不知道方向对不对"

OPC200:
✅ 记录 Day 1 里程碑
📝 标记关键决策点：方向验证
🎯 创建 7 天后回顾任务
💡 建议：下周找 3 个目标用户聊聊
```

### Day 28: 首次发布
```
你："产品上线了！虽然功能很简单，但终于有人能用了"

OPC200:
🎉 里程碑达成：首次产品发布！
📊 对比 Day 1：完成度从 0% → 100%
🔍 模式识别：你在深夜效率最高
⚠️ 风险提示：连续 5 天睡眠不足
💡 建议：庆祝一下，然后睡个好觉
```

### Day 45: 陷入低谷
```
你："连续一周没动静，是不是产品方向错了"

OPC200:
📉 检测到情绪低谷（第 3 次类似模式）
🔙 历史回顾：Day 12 也有类似焦虑，后来通过用户访谈解决
📋 推荐行动：查看之前的 3 个用户反馈
⏰ 异步任务已创建：生成竞品分析报告（明早 8 点）
💡 建议：低谷通常持续 3-5 天，你过去的应对方式是...
```

### Day 100: 百日报告
```
OPC200 自动生成：
📈 100 天成长报告
├── 里程碑：5 个达成，2 个延期
├── 工作模式：高效时段周三下午、周五上午
├── 决策风格：保守型，平均犹豫 2.3 天
├── 求助时机：通常在问题出现后 2 天
└── 成长轨迹：从"焦虑但兴奋"到"从容但有目标"

🎯 下一阶段建议：
├── 短期（30 天）：完善付费流程
├── 中期（90 天）：达到 MRR $1000
└── 长期（365 天）：考虑首次招聘
```

---

## 📦 核心 Skill

### OPC Journal

专为 OPC200 设计的单一 CLI 日志与成长追踪 Skill，包含：

| 命令 | 功能 |
|------|------|
| `init` | 初始化日志与用户章程 |
| `record` | 记录每日条目（含动态情绪分析） |
| `search` | 搜索历史条目 |
| `export` | 导出日志数据 |
| `analyze` | 模式分析与解读层 |
| `milestones` | 里程碑自动检测 |
| `insights` | 个性化洞察与建议 |
| `task` | 异步任务创建（Legacy） |
| `status` | 查看日志状态 |

文档: [SKILL.md](./skills/opc-journal/SKILL.md)

### 安装

```bash
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --skill opc-journal
```



## 🔒 安全特性

### 数据分级保护

```yaml
# 三层数据分级
tier_1_critical:    # 绝不上云
  - raw_customer_data
  - proprietary_code
  - financial_records
  
tier_2_sensitive:   # 脱敏后可同步
  - usage_patterns
  - error_logs
  - performance_metrics
  
tier_3_shareable:   # 可安全共享
  - knowledge_articles
  - best_practices
```

### 紧急访问协议

```bash
# 请求紧急访问权限
./scripts/support/vpn-manager.sh \
  --id OPC-001 \
  emergency-access \
  --reason "Gateway故障恢复" \
  --duration 2h
```

- 用户授权后才可 VPN 接入
- 所有操作审计日志
- 4小时自动超时
- 用户可随时撤销

---

## 🛠️ 运维指南

### 日常维护

```bash
# 健康检查
./scripts/maintenance/health-check.sh -i OPC-001
./scripts/maintenance/health-check.sh -m all  # 检查所有

# 创建备份
./scripts/maintenance/backup-manager.sh \
  --id OPC-001 backup

# 恢复备份
./scripts/maintenance/backup-manager.sh \
  --id OPC-001 restore \
  --name auto-20260321-120000

# 清理旧备份（保留7天）
./scripts/maintenance/backup-manager.sh \
  --id OPC-001 cleanup \
  --retention 7
```

### 故障恢复

```bash
# Gateway 故障
./scripts/recovery/emergency-recovery.sh \
  --id OPC-001 \
  --scenario gateway-failure

# 数据保险箱损坏
./scripts/recovery/emergency-recovery.sh \
  --id OPC-001 \
  --scenario data-vault-corruption

# Tailscale 断开
./scripts/recovery/emergency-recovery.sh \
  --id OPC-001 \
  --scenario tailscale-disconnect

# 模拟运行（不实际执行）
./scripts/recovery/emergency-recovery.sh \
  --id OPC-001 \
  --scenario disk-full \
  --dry-run
```

### 自动化运维

```bash
# 添加到 crontab

# 每小时健康检查
0 * * * * /opc200/scripts/maintenance/health-check.sh -m all

# 每天凌晨2点备份
0 2 * * * /opc200/scripts/maintenance/backup-manager.sh --all backup

# 每周日清理旧备份
0 3 * * 0 /opc200/scripts/maintenance/backup-manager.sh --all cleanup
```

---

## 📚 文档导航

| 文档 | 内容 |
|------|------|
| [SYSTEM.md](./SYSTEM.md) | 完整架构方案：部署分布、Tailscale VPN、数据保险箱、紧急访问 |
| [KNOWLEDGE_BASE.md](./KNOWLEDGE_BASE.md) | 知识库：最佳实践、故障排除、技能开发指南 |
| [STRUCTURE.md](./STRUCTURE.md) | 项目文件结构完整说明 |
| [docs/SCRIPTS.md](./docs/SCRIPTS.md) | 所有运维脚本的详细使用手册 |
| [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) | 本地/云端部署详细指南 |
| [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) | 技能开发与扩展指南 |
| [docs/SECURITY.md](./docs/SECURITY.md) | 安全配置与审计指南 |

---

## 🧩 系统要求

### 本地部署

- **OS**: Linux (Ubuntu 22.04+ / Debian 12+)
- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB 推荐)
- **Disk**: 100GB+ SSD
- **Network**: 可访问 Tailscale 控制平面

### 云端托管

- **K8s**: 1.28+
- **Ingress**: nginx / traefik
- **Storage**: 支持 RWO / RWX 的 StorageClass

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

[MIT License](./LICENSE) © 2026 coidea.ai

---

## 🙏 致谢

- [OpenClaw](https://openclaw.ai) - AI Agent 平台
- [ClawHub](https://clawhub.ai) - Skills 生态系统
- [Tailscale](https://tailscale.com) - 安全网络基础设施

---

> **"让 AI 成为你最可靠的合伙人"** 🤖✨
> 
> 有问题？请联系 support@coidea.ai
