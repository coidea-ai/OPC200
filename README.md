# OPC200 - One Person Company 超级智能体支持平台

> **200 个一人公司，100 天 7×24 小时超级智能体陪伴式成长**

[![Version](https://img.shields.io/badge/version-2.2-blue.svg)](./VERSION)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.3+-green.svg)](https://openclaw.ai)
[![Security](https://img.shields.io/badge/security-Data%20Vault%20Architecture-red.svg)](./SYSTEM.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

---

## 🎯 项目概述

OPC200 是一个面向 **One Person Company（一人公司）** 的 AI 智能体支持基础设施，通过 OpenClaw 平台提供持续 100 天的陪伴式成长服务。

### 核心能力

| 能力 | 说明 |
|------|------|
| **🤖 7×24 智能体陪伴** | 不只是问答，是连续 100 天的成长记录与回顾 |
| **📝 User Journal** | 三层记忆架构（会话→短期→长期），记录完整用户旅程 |
| **🔒 数据主权** | 本地数据保险箱，敏感信息绝不上云 |
| **🌐 混合部署** | 150 本地部署 + 50 云端托管 |
| **🛠️ 专属 Skills** | OPC Journal Suite 等 6+ 专属技能 |

---

## 🏗️ 架构设计

### 部署架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OPC200 部署分布 (200客户)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   本地部署 (150)                          云端托管 (50)                  │
│   ┌────────────────────────┐              ┌────────────────────────┐   │
│   │ • Tailscale VPN 连接   │              │ • 我们的 Gateway       │   │
│   │ • 敏感数据本地存储     │              │ • 共享基础设施         │   │
│   │ • 离线知识包支持       │              │ • 全权托管             │   │
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
│   └── opc-journal-suite/       # OPC Journal Suite（6个技能）
│       ├── SKILL.md             # 套件总控
│       ├── opc-journal-core/    # 核心日志
│       ├── opc-pattern-recognition/  # 模式识别
│       ├── opc-milestone-tracker/    # 里程碑追踪
│       ├── opc-async-task-manager/   # 异步任务
│       └── opc-insight-generator/    # 洞察生成
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
└── docker-compose.yml           # 服务编排（待完善）
```

---

## 🚀 快速开始

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

# 4. 安装 OPC Journal Suite
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --skill opc-journal-suite

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
  --skill opc-journal-suite
```

---

## 📦 核心 Skills

### OPC Journal Suite

专为 OPC200 设计的用户日志与成长追踪技能套件。

| Skill | 功能 | 文档 |
|-------|------|------|
| `opc-journal-core` | 日志记录、检索、摘要生成 | [SKILL.md](./skills/opc-journal-suite/opc-journal-core/SKILL.md) |
| `opc-pattern-recognition` | 行为模式分析与预测 | [SKILL.md](./skills/opc-journal-suite/opc-pattern-recognition/SKILL.md) |
| `opc-milestone-tracker` | 里程碑自动检测与庆祝 | [SKILL.md](./skills/opc-journal-suite/opc-milestone-tracker/SKILL.md) |
| `opc-async-task-manager` | 7×24 异步任务调度 | [SKILL.md](./skills/opc-journal-suite/opc-async-task-manager/SKILL.md) |
| `opc-insight-generator` | 个性化洞察与建议 | [SKILL.md](./skills/opc-journal-suite/opc-insight-generator/SKILL.md) |

### 安装单个 Skill

```bash
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --skill opc-journal-core
```

### 更新所有 Skills

```bash
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --update
```

---

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
