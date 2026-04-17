# OPC200 - One Person Company 超级智能体支持平台

> **200 个一人公司，100 天 7×24 小时超级智能体陪伴式成长**

[![Version](https://img.shields.io/badge/version-2.2-blue.svg)](./VERSION)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.3+-green.svg)](https://openclaw.ai)
[![Security](https://img.shields.io/badge/security-Data%20Vault%20Architecture-red.svg)](./SYSTEM.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

---

## 🎯 项目概述

OPC200 是一个面向 **One Person Company（一人公司）** 的 AI 智能体支持基础设施，通过 OpenClaw 平台提供持续 100 天的陪伴式成长服务。

### 架构演进

| 维度 | 旧架构（已废弃） | 新架构（开发中） |
|------|-----------------|-----------------|
| 用户端 | 5 容器（~6GB） | 1 Agent（~500MB） |
| 监控 | 各客户独立 Grafana | 平台统一监控 |
| 升级 | 逐个 SSH 升级 | 批量推送升级 |
| 网络 | Tailscale VPN | 纯 HTTPS 出站 |
| 代码位置 | `src/`, `skills/`, `config/` | `agent/`, `platform/`, `shared/` |

### 核心能力

| 能力 | 说明 |
|------|------|
| **🤖 7×24 智能体陪伴** | 不只是问答，是连续 100 天的成长记录与回顾 |
| **📝 User Journal** | 三层记忆架构（会话→短期→长期），记录完整用户旅程 |
| **🔒 数据主权** | 本地数据保险箱，敏感信息绝不上云 |
| **🌐 混合部署** | 150 本地部署 + 50 云端托管 |
| **🛠️ 专属 Skills** | OPC Journal Suite 等 6+ 专属技能 |
| **📊 平台监控** | 【新】统一监控 200 用户实例，故障主动发现 |
| **🔄 自修复** | 【新】Agent 本地自动修复 80% 常见问题 |

---

## 🏗️ 架构设计（新架构：Push 模式）

### 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OPC200 Push 架构                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   📦 平台端 (云端集中)                                                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  Pushgateway  │  Prometheus  │  Grafana  │  AlertManager       │  │
│   │  (指标接收)    │  (时序存储)   │  (可视化)  │  (告警分发)         │  │
│   │  version-control/                                           │  │
│   │  (版本管理 + 灰度发布)                                        │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                               ▲                                         │
│                               │ HTTPS ( outbound only )                │
│                               │                                         │
│   📦 用户端 (本地/云端)                                                    │
│   ┌───────────────────────────┴─────────────────────────────────────┐  │
│   │  OPC Agent (精简版 OpenClaw)                                     │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │  │
│   │  │ Gateway  │  │  Journal │  │ Exporter │──┐                   │  │
│   │  │ (精简)   │  │ (本地存储)│  │ (指标推送)│  │                   │  │
│   │  └──────────┘  └──────────┘  └──────────┘  │                   │  │
│   │  ┌──────────┐  ┌──────────┐                │                   │  │
│   │  │SelfHealer│  │ Updater  │────────────────┘                   │  │
│   │  │(自修复)  │  │(版本更新)│                                    │  │
│   │  └──────────┘  └──────────┘                                    │  │
│   │                                                                │  │
│   │  资源占用: ~500MB (原 4-6GB)                                   │  │
│   │  部署方式: 单容器一键启动                                       │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   部署分布: 150 本地部署 + 50 云端托管 = 200 用户                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 架构对比

| 维度 | 旧架构 | 新架构 (Push 模式) |
|------|--------|-------------------|
| **用户端形态** | 5 容器 (Gateway+Journal+Qdrant+Prometheus+Grafana) | 1 Agent (~500MB) |
| **监控方式** | 各客户独立 Grafana | 平台统一监控 |
| **网络要求** | Tailscale VPN + 公网/端口开放 | 纯 HTTPS 出站 |
| **升级方式** | 逐个 SSH 登录升级 | 平台批量推送 |
| **运维效率** | 200 实例逐个处理 | 统一 Dashboard 管理 |
| **资源占用** | 4-6GB / 用户 | ~500MB / 用户 |

### 核心组件

#### 📦 Agent 用户端

| 模块 | 功能 | 状态 |
|------|------|------|
| `gateway/` | 精简版 OpenClaw（去除监控组件） | 🔄 开发中 |
| `journal/` | SQLite 本地存储（原 Qdrant 降级） | ✅ 已迁移 |
| `exporter/` | Prometheus 指标推送 | 🔄 待实现 |
| `selfhealer/` | 三级自修复机制 | 🔄 待实现 |
| `updater/` | 版本更新客户端 | 🔄 待实现 |

#### 📦 Platform 平台端

| 服务 | 功能 | 端口 |
|------|------|------|
| Pushgateway | 接收所有 Agent 推送的指标 | 9091 |
| Prometheus | 统一时序存储（200 用户聚合） | 9090 |
| Grafana | 多租户可视化 Dashboard | 3000 |
| AlertManager | 统一告警路由（飞书/邮件/短信） | 9093 |
| Version Control | 版本仓库 + 灰度发布 | 8080 |

### 技术栈

- **AI 平台**: [OpenClaw](https://openclaw.ai) Gateway（精简版）
- **用户端**: Docker 单容器 / Windows / Mac / Linux 可执行文件
- **网络**: 纯 HTTPS 出站（无需 VPN、公网 IP、端口开放）
- **存储**: SQLite（本地）+ Prometheus（云端时序）
- **监控**: Prometheus + Grafana（平台统一）
- **升级**: 平台端版本管理 + Agent 自动更新

---

## 👥 多 Agent 协作

本项目采用**多 AI Agent 协同开发**模式。

### 🎯 任务板

**📋 当前任务**: [docs/TASK_BOARD.md](./docs/TASK_BOARD.md)

任务板包含：
- 11 个待实现任务（按 P0/P1/P2/P3 优先级分类）
- 任务认领规则（📥 待领取 → 🏃 进行中 → 👀 审核中 → ✅ 已完成）
- Agent 分工表
- 阻塞问题追踪

### 📝 如何参与

```bash
# 1. 查看当前任务
cat docs/TASK_BOARD.md

# 2. 认领任务（在 TASK_BOARD.md 对应任务下回复）
# 格式: "@your-agent-name 认领"

# 3. 开始开发
git checkout feat/push-architecture
# ... 编码 ...

# 4. 提交修改
git add .
git commit -m "feat(agent): implement xxx"
git push origin feat/push-architecture
```

### 🏷️ 任务优先级

| 标识 | 优先级 | 当前任务 |
|------|--------|----------|
| 🔴 P0 | 紧急 | AGENT-001 (Dockerfile), AGENT-002 (exporter) |
| 🟡 P1 | 高 | AGENT-003 (import 调整), AGENT-004 (selfhealer) 等 4 个 |
| 🟢 P2 | 中 | AGENT-007 (通信协议), AGENT-008 (版本管理) 等 3 个 |
| ⚪ P3 | 低 | AGENT-010 (删除旧目录), AGENT-011 (CI/CD) |

### 🤝 协作规则

1. **单任务制**: 一个 Agent 同时最多 **2 个** 任务
2. **认领方式**: 在 `docs/TASK_BOARD.md` 对应任务下回复 `"@agent-name 认领"`
3. **超时释放**: 任务 48 小时无更新自动标记为 `"待重新认领"`
4. **阻塞上报**: 遇到阻塞立即标记状态并 `@other-agent` 协助

### 📊 实时状态

查看完整任务板: **[docs/TASK_BOARD.md](./docs/TASK_BOARD.md)**

| 状态 | 数量 |
|------|------|
| 📥 待领取 | 11 |
| 🏃 进行中 | 0 |
| 👀 审核中 | 0 |
| ✅ 已完成 | 0 |

---

## ⚠️ 重要：项目正在架构改造中

> **当前分支**: `feat/push-architecture`  
> **改造目标**: 从私有化全容器部署转向 Push 模式集中监控架构  
> **任务板**: [docs/TASK_BOARD.md](./docs/TASK_BOARD.md)

我们正在将项目重构为**平台侧**和**用户侧**双架构，以支持 200 用户规模化运营。

---

## 📁 项目结构（新架构）

```
opc200/
│
├── README.md                    # 📍 本文件
├── SYSTEM.md                    # 架构方案文档（核心）
├── KNOWLEDGE_BASE.md            # 知识库与最佳实践
├── STRUCTURE.md                 # 项目文件结构
├── LICENSE                      # MIT 许可证
│
├── 📦 agent/                    # 【新】用户侧（OPC Agent）
│   ├── src/                     #   Agent 源代码
│   │   ├── gateway/             #     精简版 OpenClaw Gateway
│   │   ├── journal/             #     本地 SQLite 存储
│   │   ├── exporter/            #     指标推送到平台
│   │   ├── selfhealer/          #     自修复机制
│   │   └── updater/             #     版本更新客户端
│   ├── config/                  #   Agent 配置文件
│   ├── skills/                  #   用户侧 Skills
│   └── README.md                #   Agent 使用说明
│
├── 📦 platform/                 # 【新】平台侧（云端集中）
│   ├── pushgateway/             #   指标接收服务
│   ├── prometheus/              #   时序存储
│   ├── grafana/                 #   可视化 Dashboard
│   ├── alertmanager/            #   告警路由
│   ├── version-control/         #   版本管理 + 灰度发布
│   └── README.md                #   平台部署说明
│
├── 🔗 shared/                   # 【新】共享组件
│   ├── proto/                   #   通信协议定义
│   ├── pkg/                     #   共享工具包
│   └── README.md
│
├── 📚 docs/                     # 文档
│   ├── SCRIPTS.md               #   脚本使用手册
│   ├── DEPLOYMENT.md            #   部署指南
│   ├── ARCHITECTURE.md          #   【新】Push 架构设计
│   ├── TASK_BOARD.md            #   【新】多 Agent 任务板
│   └── ...
│
└── 🔧 scripts/                  # 运维脚本
    ├── setup/                   #   初始化脚本
    ├── deploy/                  #   部署脚本
    ├── maintenance/             #   维护脚本
    └── ...
```

### 🗂️ 旧目录说明（待迁移/删除）

以下目录为**旧架构遗留**，已复制到新位置，后续将删除：

| 旧目录 | 状态 | 新位置 | 说明 |
|--------|------|--------|------|
| `src/` | ⚠️ 旧 | `agent/src/` | 源代码已迁移 |
| `skills/` | ⚠️ 旧 | `agent/skills/` | Skills 已迁移 |
| `config/` | ⚠️ 旧 | `agent/config/` | 配置已迁移 |
| `monitoring/` | ⚠️ 旧 | `platform/prometheus/` `platform/grafana/` | 监控组件已迁移 |
| `Dockerfile` | ⚠️ 旧 | - | 将被 `agent/Dockerfile` 替代 |
| `Dockerfile.gateway` | ⚠️ 旧 | `agent/src/gateway/` | 参考用 |
| `docker-compose.yml` | ⚠️ 旧 | `agent/docker-compose.yml` `platform/docker-compose.yml` | 将拆分 |

> 💡 **新开发请使用 `agent/` 和 `platform/` 目录**，旧目录仅保留用于对照和回退。

---

## 🚀 快速开始（新架构）

### 构建 Agent（用户侧）

```bash
cd agent
docker build -t opc-agent:latest .
docker run -d \
  --name opc-agent \
  -v ~/.opc200:/data \
  -e PLATFORM_URL=https://opc200.co \
  -e TENANT_ID=opc-001 \
  opc-agent:latest
```

### 部署平台（云端）

```bash
cd platform
docker-compose up -d
```

---

## 📋 原项目结构（旧架构）

> 以下内容为旧架构文档，仅供参考。新架构请参考 `agent/README.md` 和 `platform/README.md`。

<details>
<summary>点击展开旧架构说明（已废弃）</summary>

```
opc200/
│
├── skills/                      # OpenClaw Skills
│   └── opc-journal/             # OPC Journal (single unified skill)
│       ├── SKILL.md
│       ├── GUIDE.md
│       ├── CHANGELOG.md
│       ├── scripts/
│       ├── utils/
│       └── tests/
│
├── scripts/                     # 运维脚本
│   ├── setup/                   # 初始化脚本
│   ├── deploy/                  # 部署脚本
│   ├── maintenance/             # 维护脚本
│   ├── support/                 # 支持脚本
│   └── recovery/                # 恢复脚本
│
└── docker-compose.yml           # 服务编排
```

</details>

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
openclaw run "/opc-journal init --day 1 --goals '完成产品原型,获得首个付费用户'"

# 4. 开始记录（自然语言即可）
openclaw chat "今天完成了用户注册功能，但数据库选型有点纠结"
# 系统自动：创建日志条目 + 标记情绪状态 + 创建后续任务

# 5. 查看成长轨迹（第 7 天示例）
openclaw run "/opc-journal insights --day 7"
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

## 📦 核心 Skills

### opc-journal

专为 OPC200 设计的用户日志与成长追踪技能。v2.5.2 版本采用 interpretation-first 架构，所有数据本地存储。

| 功能模块 | 说明 | 命令示例 |
|---------|------|---------|
| 日志记录 | 追加式条目记录 | `/opc-journal record "今日进展"` |
| 全文搜索 | 本地文件搜索 | `/opc-journal search --query "关键词"` |
| 导出 | Markdown/JSON 导出 | `/opc-journal export --format markdown` |
| 模式分析 | 结构化信号提取 | `/opc-journal analyze --days 7` |
| 里程碑 | 里程碑检测 | `/opc-journal milestones` |
| 洞察生成 | 上下文聚合与信号统计 | `/opc-journal insights --days 30` |
| 任务管理 | 持久化异步任务 | `/opc-journal task --description "调研"` |
| 归档 | 备份与清理 | `/opc-journal archive --clear` |

**完整文档**: [GUIDE.md](./skills/opc-journal/GUIDE.md) | [CHANGELOG.md](./skills/opc-journal/CHANGELOG.md)

### 安装 opc-journal

```bash
./scripts/deploy/install-skills.sh \
  --id OPC-001 \
  --skill opc-journal
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

### 新架构文档

| 文档 | 内容 |
|------|------|
| [agent/README.md](./agent/README.md) | **【新】** Agent 用户侧使用说明 |
| [platform/README.md](./platform/README.md) | **【新】** Platform 平台侧部署说明 |
| [docs/TASK_BOARD.md](./docs/TASK_BOARD.md) | **【新】** 多 Agent 协同任务板 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | **【新】** Push 架构完整设计 |
| [docs/architecture/DIRECTORY_MIGRATION.md](./docs/architecture/DIRECTORY_MIGRATION.md) | **【新】** 目录迁移详细说明 |

### 原有文档（仍适用）

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
