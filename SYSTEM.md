# OPC200 最终架构方案

> **目标**: 200 个 One Person Company，100 天 7×24 小时超级智能体支持  
> **核心差异化**: User Journal 体验 + Skills 化架构 + 混合部署  
> **版本**: v2.2 Final  
> **日期**: 2026-03-21

---

## 一、部署分布概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OPC200 部署分布 (200客户)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   本地部署 (20)                           云端托管 (180)                 │
│   ┌────────────────────────┐              ┌────────────────────────┐   │
│   │ 自主可控 + 数据敏感     │              │ 开箱即用 + 低运维       │   │
│   │                        │              │                        │   │
│   │ • Tailscale VPN 连接   │              │ • 多租户共享基础设施    │   │
│   │ • 敏感数据本地存储     │              │ • Gateway-per-tenant   │   │
│   │ • All-in-One 容器      │              │ • 自动备份到 S3/B2     │   │
│   │ • 紧急远程访问授权     │              │                        │   │
│   │                        │              │                        │   │
│   │ OPC-001 ~ OPC-020      │              │ OPC-021 ~ OPC-200      │   │
│   └────────────────────────┘              └────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                    支持中心 (Support Hub)                    │      │
│   │  • 统一调度引擎  • 分级知识库  • 统一监控  • 应急响应中心     │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Tailscale VPN 网络架构

### 2.1 网状网络拓扑

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Tailscale 网状网络 (Tailnet)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────────┐                                                  │
│   │   支持中心        │                                                  │
│   │ (Control Plane)  │                                                  │
│   │ • ACL 管理       │                                                  │
│   │ • 密钥分发       │                                                  │
│   └────────┬─────────┘                                                  │
│            │                                                            │
│   ┌────────┴─────────────────────────┐                                  │
│   │                                  │                                  │
│   ▼                                  ▼                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│ │ 支持工程师   │  │  监控节点    │  │  知识库节点  │                      │
│ │(标签:support)│  │(标签:monitor)│  │(标签:knowledge)│                      │
│ └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                         │
│ ═══════════════════════════════════════════════════════════════════    │
│                        客户节点 (150个)                                  │
│                                                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│ │  OPC-001    │  │  OPC-002    │  │  OPC-150    │                      │
│ │  Gateway    │  │  Gateway    │  │  Gateway    │                      │
│ │ (标签:opc)  │  │ (标签:opc)  │  │ (标签:opc)  │                      │
│ │ 紧急访问:启用│  │ 紧急访问:启用│  │ 紧急访问:启用│                      │
│ └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 ACL 策略

```yaml
# tailscale-acl.yml
acls:
  # 支持工程师可访问客户节点
  - action: accept
    src: ["tag:support"]
    dst: ["tag:opc:*"]
    
  # 客户不可反向访问支持中心
  - action: deny
    src: ["tag:opc"]
    dst: ["tag:support", "tag:knowledge:write"]
    
  # 客户可只读访问知识库
  - action: accept
    src: ["tag:opc"]
    dst: ["tag:knowledge:80,443"]
    
  # 客户间完全隔离
  - action: deny
    src: ["tag:opc"]
    dst: ["tag:opc"]
```

**安全原则**:
- 平时：支持中心 **无法访问** 客户数据
- 紧急：客户授权后才可 VPN 接入
- 所有操作审计日志
- 客户可随时撤销访问

---

## 三、敏感信息控制体系（本地部署）

### 3.0 Agent-Blind Credentials 架构

OPC200 采用 [OpenClaw RFC #9676](https://github.com/openclaw/openclaw/discussions/9676) 提出的 Agent-Blind Credentials 安全架构：

```
┌─────────────────────────────────────────────────────────────┐
│               Agent-Blind Credentials 架构                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Agent 层（只可见元数据）                                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ • 凭证名称                                           │  │
│   │ • 凭证类型 (api_key/password/token)                 │  │
│   │ • 元数据 (service, scope, expires_at)               │  │
│   │ • 轮换提示                                           │  │
│   │                                                     │  │
│   │ ❌ 凭证值（加密存储，Agent 无法访问）                  │  │
│   └─────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼ 服务层授权                         │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              SecureVault (数据保险箱)                │  │
│   │ • AES-256-GCM 加密                                  │  │
│   │ • 审计日志                                          │  │
│   │ • 自动轮换提醒                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**安全优势**:
- Agent 即使被提示注入攻击，也无法泄露凭证值
- 凭证访问需要明确的服务层授权
- 所有访问操作都被审计

### 3.1 数据分级

```yaml
# data-classification.yml
data_classification:
  tier_1_critical:        # 绝不允许离开本地
    - raw_customer_data   # 原始客户数据
    - proprietary_code    # 专有代码
    - financial_records   # 财务记录
    local_only: true
    
  tier_2_sensitive:       # 脱敏后可同步
    - usage_patterns      # 使用模式（脱敏）
    - error_logs          # 错误日志（脱敏）
    - performance_metrics # 性能指标
    encryption: required
    
  tier_3_shareable:       # 可安全共享
    - knowledge_articles  # 知识文章
    - best_practices      # 最佳实践
    - public_docs         # 公开文档
```

### 3.2 数据保险箱结构

```
customers/on-premise/opc-{id}/
├── data-vault/                    # 数据保险箱
│   ├── encrypted/                 # 加密存储
│   │   ├── keys/                  # 客户自有密钥
│   │   └── vault.db               # 加密数据库
│   │
│   ├── local-only/                # 绝不上云
│   │   ├── sensitive-memory/      # 敏感记忆
│   │   ├── private-codebases/     # 私有代码库
│   │   └── customer-data/         # 客户业务数据
│   │
│   └── audit-trail/               # 审计追踪
│       ├── access-logs/           # 访问日志
│       ├── sync-logs/             # 同步日志
│       └── emergency-access/      # 紧急访问记录
│
└── compliance/
    ├── data-residency.yml         # 数据驻留声明
    ├── encryption-manifest.yml    # 加密清单
    └── audit-reports/             # 合规审计报告
```

### 3.3 紧急访问协议

```yaml
# emergency-access-protocol.yml
emergency_access:
  trigger_conditions:
    - system_unresponsive > 30min
    - data_loss_detected
    - customer_explicit_request
    
  authorization:
    tier_1: customer_self_service      # 客户自助
    tier_2: support_with_notice        # 通知后访问
    tier_3: break_glass                # 紧急破窗
    
  audit_requirements:
    record_all_commands: true
    session_recording: required
    customer_notification: immediate
    post_access_report: within 1h
    
  revocation:
    automatic_timeout: 4h
    manual_revoke: customer_can_revoke_anytime
```

**紧急支持流程**:
```
用户发起求助
    │
    ▼
支持工程师申请访问
    │
    ▼
用户授权（飞书确认）
    │
    ▼
临时 VPN 接入（4h 有效，可撤销）
    │
    ▼
解决问题 → 断开连接 → 审计日志归档
```

---

## 四、离线知识包（Offline Knowledge Pack）

### 4.1 知识包结构

```
knowledge-packs/
├── latest/                              # 最新版本
│   └── opc200-knowledge-pack-v2.4.1.tar.gz
│
├── archive/                             # 历史版本
│   └── v2.4.0/
│
└── contents/                            # 内容清单
    ├── skills/                          # 离线 Skills
    │   ├── essential/                   # 核心技能
    │   │   ├── file-operations/
    │   │   ├── git-basics/
    │   │   └── system-health/
    │   │
    │   └── extended/                    # 扩展技能
    │
    ├── knowledge-base/                  # 离线知识库
    │   ├── troubleshooting/             # 故障排除
    │   ├── best-practices/              # 最佳实践
    │   └── faq/                         # 常见问题
    │
    ├── models/                          # 本地模型（可选）
    │   └── tinyllama-1.1b/              # 轻量本地模型
    │
    └── update-mechanism/                # 更新机制
        ├── diff-updates/                # 增量更新
        └── checksums/                   # 完整性校验
```

### 4.2 离线运行模式

```yaml
# offline-mode.yml
offline_mode:
  trigger:
    network_unavailable: "> 5min"
    
  capabilities:
    file_operations: full
    git_operations: full
    local_search: full
    code_assistance: limited    # 使用本地小模型
    web_search: disabled
    external_apis: disabled
    
  sync_on_reconnect:
    local_changes: push
    knowledge_pack_updates: check
    session_logs: upload
```

**离线场景支持**:
- 网络中断 > 5 分钟自动进入离线模式
- 核心功能（文件、Git、本地搜索）正常工作
- 代码辅助降级为本地小模型
- 网络恢复后自动同步

---

## 五、User Journal 体验（核心价值）

### 5.1 不是聊天记录，是成长叙事

**传统 AI**: 用完即走的问答  
**OPC200**: 连续 100 天的陪伴式成长记录

```
Day 1 ─── Day 30 ─── Day 60 ─── Day 100
  │          │          │          │
启动期    建立期     加速期     自主期
  │          │          │          │
认识系统  形成习惯   委托复杂   成为指挥官
设定目标  首次胜利   多 Agent   百日成就
```

### 5.2 三层记忆（基于 OpenClaw Memory Masterclass）

| 层次 | 用户感知 | 技术实现 | OpenClaw 配置 |
|------|---------|---------|--------------|
| **即时** | "它记得我5分钟前说的话" | 会话上下文 | `context_window` |
| **短期** | "它记得上周的讨论" | 语义检索 | `memory_search` + 向量存储 |
| **长期** | "它了解我的工作风格" | 模式识别 + 用户画像 | `MEMORY.md` + 定期分析 |

**OpenClaw 三层防御配置**:

```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "reserveTokensFloor": 40000,
        "memoryFlush": {
          "enabled": true,
          "softThresholdTokens": 4000,
          "systemPrompt": "Session nearing compaction. Store durable memories now.",
          "prompt": "Write any lasting notes to memory/YYYY-MM-DD.md; reply with NO_REPLY if nothing to store."
        }
      }
    }
  },
  "memory": {
    "heartbeatCheck": {
      "enabled": true,
      "checkIntervalMinutes": 30
    }
  }
}
```

**文件架构**:
- `SOUL.md` - 人格与行为规则（每会话读取）
- `MEMORY.md` - 精选长期记忆（每会话读取，保持简洁 < 100 行）
- `memory/YYYY-MM-DD.md` - 日常日志（自动归档）

### 5.3 7×24 陪伴节奏

| 时段 | 模式 | 典型交互 |
|------|------|---------|
| 06-09 | 温和启动 | 隔夜任务更新、今日优先事项 |
| 09-12 | 高效执行 | 深度工作支持、Agent 优先 |
| 12-14 | 轻松交流 | 行业资讯、轻松问答 |
| 14-18 | 协作模式 | 多 Agent 协作、复杂任务 |
| 18-22 | 反思总结 | Journal 摘要、明日预备 |
| 22-06 | 静默守护 | 后台任务执行、紧急监控 |

---

## 六、Skills 化设计

### 6.1 OPC Journal Suite（6个 Skills）

```
┌─────────────────────────────────────────────────────────────┐
│                  OPC Journal Suite                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Journal   │  │   Pattern   │  │  Milestone  │        │
│  │    Core     │──┤ Recognition │──┤   Tracker   │        │
│  └──────┬──────┘  └─────────────┘  └─────────────┘        │
│         │                                                   │
│         │  ┌─────────────┐  ┌─────────────┐                │
│         └──┤    Async    │  │   Insight   │                │
│            │  Task Mgr   │  │  Generator  │                │
│            └─────────────┘  └─────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| Skill | 功能 | 发布状态 |
|-------|------|---------|
| `opc-journal-core` | 日志记录、检索、摘要 | 🟡 待发布 |
| `opc-pattern-recognition` | 行为模式分析 | 🟡 待发布 |
| `opc-milestone-tracker` | 里程碑检测与庆祝 | 🟡 待发布 |
| `opc-async-task-manager` | 7×24 异步任务 | 🟡 待发布 |
| `opc-insight-generator` | 洞察与建议 | 🟡 待发布 |
| `opc-journal-suite` | 完整套件 | 🟡 待发布 |

### 6.2 客户安装

```bash
# 云端：我们预装
# 本地：客户自助
clawhub install coidea/opc-journal-suite
```

---

## 七、实施计划

### Phase 1: 基础设施 (Days 1-7)

| 任务 | 负责 | 输出 |
|------|------|------|
| Tailscale Control Plane | 我们 | `tailscale.opc200.co` |
| 云端 Gateway 集群 | 我们 | `gateway-cloud.opc200.co` |
| 监控与日志平台 | 我们 | `monitor.opc200.co` |
| 离线知识包 v1.0 | 我们 | `opc200-knowledge-pack-v1.0.tar.gz` |

### Phase 2: 首批客户 (Days 8-14)

| 客户 | 模式 | 验证目标 |
|------|------|---------|
| OPC-001~010 | 本地 | Tailscale 接入 + 数据保险箱 |
| OPC-151~155 | 云端 | 标准 onboarding 流程 |

### Phase 3: 批量部署 (Days 15-60)

| 阶段 | 目标 | 数量 |
|------|------|------|
| Sprint 1 | 云端客户 | 60个 (OPC-021~080) |
| Sprint 2 | 云端客户 | 60个 (OPC-081~140) |
| Sprint 3 | 云端客户 | 60个 (OPC-141~200) |
| Sprint 4 | 本地客户 | 20个 (OPC-001~020) |

### Phase 4: 稳定运行 (Days 61-100)

- 全量监控覆盖（云端共享基础设施 + 本地 all-in-one监控）
- 7×24 值班体系
- 知识库持续更新
- Phase 2 规划

---

## 八、关键指标

| 指标 | 目标 | 备注 |
|------|------|------|
| 客户数 | 200（20本地 + 180云端） | v2.4 重构后比例 |
| 支持周期 | 100 天 7×24 小时 | |
| Token 消耗 | 10 亿 / 100天 | |
| 可用性 SLA | 99.95% | |
| 首次响应 | < 5 分钟 | |
| 紧急支持接入 | < 15 分钟 | 仅针对本地客户 |

---

## 九、启动前最终确认

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 20:180 本地/云端比例 | ✅ 确认 | v2.4 基于运维可行性重新调整 |
| Tailscale VPN 支持通道 | ✅ 确认 | 仅限 20 本地客户 |
| 云端多租户共享架构 | ✅ 确认 | `docker-compose.cloud.yml` |
| 本地 All-in-One 部署 | ✅ 确认 | `Dockerfile.allinone` |
| 紧急情况远程访问授权 | ✅ 确认 | 需客户签署授权书 |
| 敏感信息控制（数据保险箱）| ✅ 确认 | |
| 离线知识包支持 | ✅ 确认 | |

---

**v2.4 重构说明**: 在 2026-04-10 的批判性分析后，OPC200 从"大而全的 Journal 工具集"转身成为"One Person Company 的 100 天成长协议"。部署比例从 150:50 调整为 20:180，以更现实地支撑规模化运营。
