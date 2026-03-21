# OPC200 项目文件结构

```
opc200/                                      # 项目根目录
│
├── README.md                                # 项目总览与快速开始
├── SYSTEM.md                                # 架构方案（核心文档）
├── KNOWLEDGE_BASE.md                        # 知识库与最佳实践
├── OPERATIONS.md                            # 运维手册
├── docker-compose.yml                       # 服务编排
├── .env.example                             # 环境变量模板
├── .gitignore                               # Git 忽略规则
│
├── skills/                                  # OpenClaw Skills（可发布）
│   │
│   ├── opc-journal-suite/                   # 套件总控
│   │   ├── SKILL.md                         # Skill 定义与使用说明
│   │   ├── README.md                        # 详细文档
│   │   ├── config.yml                       # 默认配置
│   │   └── scripts/
│   │       └── install-suite.sh             # 一键安装脚本
│   │
│   ├── opc-journal-core/                    # 核心日志
│   │   ├── SKILL.md
│   │   ├── config.yml
│   │   └── scripts/
│   │       ├── init.py                      # 初始化 Journal
│   │       ├── record.py                    # 记录条目
│   │       ├── query.py                     # 查询检索
│   │       ├── digest.py                    # 生成摘要
│   │       └── templates/
│   │           └── entry_template.yml       # 条目模板
│   │
│   ├── opc-pattern-recognition/             # 模式识别
│   │   ├── SKILL.md
│   │   ├── config.yml
│   │   └── scripts/
│   │       ├── analyzer.py                  # 分析器
│   │       ├── patterns.py                  # 模式定义
│   │       └── predictor.py                 # 预测模型
│   │
│   ├── opc-milestone-tracker/               # 里程碑追踪
│   │   ├── SKILL.md
│   │   ├── config.yml
│   │   └── scripts/
│   │       ├── detector.py                  # 里程碑检测
│   │       ├── reporter.py                  # 报告生成
│   │       └── celebration.py               # 庆祝仪式
│   │
│   ├── opc-async-task-manager/              # 异步任务管理
│   │   ├── SKILL.md
│   │   ├── config.yml
│   │   └── scripts/
│   │       ├── scheduler.py                 # 任务调度
│   │       ├── executor.py                  # 任务执行
│   │       └── notifier.py                  # 完成通知
│   │
│   └── opc-insight-generator/               # 洞察生成
│       ├── SKILL.md
│       ├── config.yml
│       └── scripts/
│           ├── generator.py                 # 洞察生成
│           └── recommender.py               # 建议推荐
│
├── platform/                                # 平台核心（不发布）
│   │
│   ├── coordination/                        # 调度引擎
│   │   ├── router.py                        # 部署模式路由
│   │   ├── tailscale-controller.py          # Tailscale 控制
│   │   ├── load-balancer.py                 # 负载均衡
│   │   └── health-check.py                  # 健康检查
│   │
│   ├── knowledge-base/                      # 统一知识库
│   │   ├── shared/                          # 共享知识
│   │   │   ├── best-practices/              # 最佳实践
│   │   │   ├── runbooks/                    # 运维手册
│   │   │   └── templates/                   # 模板库
│   │   │
│   │   ├── cloud-only/                      # 云端功能
│   │   │   └── advanced-analytics/          # 高级分析
│   │   │
│   │   └── offline-packages/                # 离线安装包
│   │       ├── opc-journal-suite-v1.0.0.tar.gz
│   │       └── agent-team-orch-v2.1.0.tar.gz
│   │
│   └── monitoring/                          # 统一监控
│       ├── cloud-collector/                 # 云端采集器
│       │   ├── metrics.py
│       │   └── alerts.yml
│       │
│       └── onprem-collector/                # 本地采集器（VPN）
│           ├── agent.py
│           └── tailscale-metrics.py
│
├── customers/                               # 客户管理
│   │
│   ├── _template/                           # 部署模板（复用）
│   │   ├── on-premise/                      # 本地模板
│   │   │   ├── deployment/
│   │   │   │   ├── docker-compose.yml
│   │   │   │   ├── install.sh               # 安装脚本
│   │   │   │   ├── tailscale-setup.sh       # VPN 设置
│   │   │   │   └── skills-install.sh        # Skills 安装
│   │   │   │
│   │   │   ├── data-vault/                  # 数据保险箱
│   │   │   │   ├── journal/                 # Journal 存储
│   │   │   │   ├── conversations/           # 对话历史
│   │   │   │   ├── user-profile/            # 用户画像
│   │   │   │   └── backup/                  # 本地备份
│   │   │   │
│   │   │   ├── tailscale/                   # VPN 配置
│   │   │   │   ├── auth-key
│   │   │   │   └── node-info.yml
│   │   │   │
│   │   │   └── config/
│   │   │       ├── gateway.yml
│   │   │       └── skills.yml
│   │   │
│   │   └── cloud-hosted/                    # 云端模板
│   │       └── ...
│   │
│   ├── on-premise/                          # 150 本地客户
│   │   ├── registry.yml                     # 本地客户注册表
│   │   │
│   │   ├── OPC-001/                         # 客户实例
│   │   │   ├── deployment/                  # 部署配置
│   │   │   ├── data-vault/                  # 数据（加密）
│   │   │   └── tailscale/                   # VPN 配置
│   │   │
│   │   ├── OPC-002/
│   │   │   └── ...
│   │   │
│   │   └── OPC-150/
│   │       └── ...
│   │
│   ├── cloud-hosted/                        # 50 云端客户
│   │   ├── registry.yml
│   │   ├── OPC-151/
│   │   ├── OPC-152/
│   │   └── ...
│   │
│   └── registry/                            # 统一注册中心
│       ├── master-index.yml                 # 主索引
│       ├── tailscale-nodes.yml              # VPN 节点
│       └── profiles/                        # 客户画像
│           ├── OPC-001.yml
│           └── ...
│
├── support/                                 # 支持与运维
│   │
│   ├── tailscale/                           # VPN 管理
│   │   ├── control-server/                  # 控制服务器
│   │   ├── acl-configs/                     # 访问控制
│   │   └── emergency-access/                # 紧急访问
│   │
│   ├── runbooks/                            # 运维手册
│   │   ├── onboarding.md                    # 客户接入
│   │   ├── troubleshooting.md               # 故障排查
│   │   ├── emergency-response.md            # 紧急响应
│   │   └── skills-update.md                 # Skills 更新
│   │
│   └── tools/                               # 支持工具
│       ├── customer-init.sh                 # 客户初始化
│       ├── health-check.sh                  # 健康检查
│       ├── backup-manager.py                # 备份管理
│       └── vpn-connect.sh                   # VPN 连接
│
├── scripts/                                 # 自动化脚本
│   ├── setup/                               # 初始化脚本
│   │   ├── customer-init.sh                 # ⭐ 客户初始化
│   │   ├── init-tailscale.sh
│   │   ├── init-gateway.sh
│   │   └── init-monitoring.sh
│   │
│   ├── deploy/                              # 部署脚本
│   │   ├── deploy-onprem.sh                 # ⭐ 本地部署
│   │   ├── deploy-cloud.sh                  # ⭐ 云端部署
│   │   ├── install-skills.sh                # ⭐ Skills 安装
│   │   └── rolling-update.sh
│   │
│   ├── maintenance/                         # 维护脚本
│   │   ├── health-check.sh                  # ⭐ 健康检查
│   │   ├── backup-manager.sh                # ⭐ 备份管理
│   │   ├── update-skills.sh
│   │   ├── rotate-logs.sh
│   │   ├── cleanup.sh
│   │   └── offline-pack-sync.sh             # ⭐ 离线包同步
│   │
│   ├── support/                             # 支持脚本
│   │   ├── vpn-manager.sh                   # ⭐ VPN 管理
│   │   ├── emergency-access.sh
│   │   ├── remote-session.sh
│   │   └── customer-communication.sh
│   │
│   ├── recovery/                            # 恢复脚本
│   │   ├── emergency-recovery.sh            # ⭐ 紧急恢复
│   │   ├── data-vault-repair.sh
│   │   ├── gateway-rebuild.sh
│   │   └── tailscale-reconnect.sh
│   │
│   └── monitoring/                          # 监控脚本
│       ├── metrics-collector.sh
│       ├── alert-generator.sh
│       └── report-generator.sh
│
├── monitoring/                              # 监控配置
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── datasources.yml
│   └── alerts/
│       └── alertmanager.yml
│
├── disaster-recovery/                       # 故障恢复
│   ├── plans/
│   │   ├── gateway-failure.md
│   │   ├── data-corruption.md
│   │   └── vpn-outage.md
│   ├── backups/
│   └── tests/
│       └── drill-schedule.yml
│
├── docs/                                    # 文档
│   ├── architecture/                        # 架构文档
│   │   ├── overview.md
│   │   ├── journal-experience.md
│   │   └── skills-design.md
│   │
│   ├── deployment-guides/                   # 部署指南
│   │   ├── cloud-hosted.md
│   │   ├── on-premise.md
│   │   └── tailscale-setup.md
│   │
│   ├── api-reference/                       # API 文档
│   │   └── skills-api.md
│   │
│   └── user-guides/                         # 用户指南
│       ├── getting-started.md
│       ├── journal-guide.md
│       └── faq.md
│
├── tests/                                   # 测试
│   ├── unit/                                # 单元测试
│   ├── integration/                         # 集成测试
│   └── e2e/                                 # 端到端测试
│
└── memory/                                  # 项目记忆（内部）
    ├── 2026-03-21.md                        # 每日记录
    └── MEMORY.md                            # 长期记忆
```

---

## 关键路径说明

### 1. Skills 开发路径
```
skills/opc-{name}/
├── SKILL.md              # 必须：Skill 定义
├── config.yml            # 可选：默认配置
└── scripts/              # 必须：执行脚本
    └── *.py
```

### 2. 客户部署路径
```
customers/on-premise/OPC-{XXX}/
├── deployment/           # 部署配置
├── data-vault/           # 数据保险箱（敏感）
└── tailscale/            # VPN 配置
```

### 3. 文档读取顺序
```
1. README.md              # 先读我
2. SYSTEM.md              # 架构方案
3. KNOWLEDGE_BASE.md      # 知识库
4. OPERATIONS.md          # 运维手册
```

---

## 文件大小预估

| 目录 | 预估大小 | 说明 |
|------|---------|------|
| `skills/` | ~500 KB | 代码 + 文档 |
| `platform/` | ~1 MB | 核心平台代码 |
| `customers/` | ~50 MB | 配置（不含数据） |
| `docs/` | ~2 MB | 完整文档 |
| `monitoring/` | ~500 KB | 监控配置 |
| **总计** | **~55 MB** | 不含客户数据 |

---

## 待创建文件清单

**高优先级（启动前）:**
- [ ] `README.md`
- [ ] `OPERATIONS.md`
- [ ] `docker-compose.yml`
- [ ] `skills/*/scripts/*.py`
- [ ] `platform/coordination/*.py`
- [ ] `scripts/setup/*.sh`

**中优先级（试点前）:**
- [ ] `docs/deployment-guides/*.md`
- [ ] `support/runbooks/*.md`
- [ ] `monitoring/*`
- [ ] `tests/*`

**低优先级（运营后）:**
- [ ] `disaster-recovery/*`
- [ ] `docs/user-guides/*`
