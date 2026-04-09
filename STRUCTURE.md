# OPC200 项目文件结构

> **版本**: v2.2 | **更新日期**: 2026-03-24

```
opc200/                                      # 项目根目录
│
├── README.md                                # 项目总览与快速开始
├── SYSTEM.md                                # 架构方案（核心文档）
├── KNOWLEDGE_BASE.md                        # 知识库与最佳实践
├── STRUCTURE.md                             # 本文件：项目结构说明
├── LICENSE                                  # MIT 许可证
│
├── VERSION                                  # 版本号
├── CHANGELOG.md                             # 变更日志
│
├── Makefile                                 # 开发命令
├── pyproject.toml                           # Python 项目配置
├── .pre-commit-config.yaml                  # Pre-commit hooks
├── .gitignore                               # Git 忽略规则
│
├── requirements.txt                         # 生产依赖
├── requirements-dev.txt                     # 开发依赖
└── requirements-test.txt                    # 测试依赖
│
├── Dockerfile.gateway                       # Gateway 镜像
├── Dockerfile.journal                       # Journal 服务镜像
├── Dockerfile.test                          # 测试环境镜像
├── Dockerfile.prod                          # 生产环境镜像
│
├── docker-compose.yml                       # 开发环境编排
├── docker-compose.test.yml                  # 测试环境编排
└── docker-compose.prod.yml                  # 生产环境编排
│
├── .github/                                 # GitHub 配置
│   └── workflows/                           # CI/CD 工作流
│       ├── ci.yml                           # 持续集成
│       ├── security-audit.yml               # 安全审计
│       ├── deploy-staging.yml               # 测试环境部署
│       └── deploy-production.yml            # 生产环境部署
│
├── src/                                     # Python 核心模块
│   ├── __init__.py
│   │
│   ├── journal/                             # 日志模块
│   │   ├── __init__.py
│   │   ├── core.py                          # 日志CRUD、查询、摘要
│   │   ├── storage.py                       # 加密存储、备份
│   │   └── vector_store.py                  # 向量搜索、嵌入
│   │
│   ├── security/                            # 安全模块
│   │   ├── __init__.py
│   │   ├── vault.py                         # 数据保险箱
│   │   └── encryption.py                    # 加密工具集
│   │
│   ├── patterns/                            # 模式分析
│   │   ├── __init__.py
│   │   └── analyzer.py                      # 行为模式检测
│   │
│   ├── tasks/                               # 任务调度
│   │   ├── __init__.py
│   │   └── scheduler.py                     # 异步任务调度
│   │
│   └── insights/                            # 洞察生成
│       ├── __init__.py
│       └── generator.py                     # 洞察与建议
│
├── tests/                                   # 测试套件（TDD）
│   ├── conftest.py                          # pytest 配置和 fixtures
│   ├── pytest.ini                           # pytest 配置
│   │
│   ├── unit/                                # 单元测试
│   │   ├── journal/
│   │   │   ├── test_core.py
│   │   │   ├── test_storage.py
│   │   │   └── test_vector_store.py
│   │   ├── security/
│   │   │   ├── test_vault.py
│   │   │   └── test_encryption.py
│   │   ├── patterns/
│   │   │   └── test_analyzer.py
│   │   ├── tasks/
│   │   │   └── test_scheduler.py
│   │   └── insights/
│   │       └── test_generator.py
│   │
│   ├── integration/                         # 集成测试
│   │   ├── test_journal_flow.py
│   │   ├── test_security_flow.py
│   │   └── test_end_to_end.py
│   │
│   └── e2e/                                 # 端到端测试
│       └── test_user_journey.py
│
├── skills/                                  # OpenClaw Skills（可发布）
│   │
│   ├── opc-journal-suite/                   # OPC Journal Suite
│   │   ├── SKILL.md                         # 套件总控文档
│   │   │
│   │   ├── opc-journal-core/                # 核心日志
│   │   │   ├── SKILL.md
│   │   │   ├── config.yml
│   │   │   └── scripts/
│   │   │       ├── init.py
│   │   │       ├── record.py
│   │   │       ├── query.py
│   │   │       └── digest.py
│   │   │
│   │   ├── opc-pattern-recognition/         # 模式识别 (v2.4→解读层)
│   │   │   ├── SKILL.md
│   │   │   ├── config.yml
│   │   │   └── scripts/
│   │   │       ├── analyzer.py
│   │   │       └── predictor.py
│   │   │
│   │   ├── opc-milestone-tracker/           # 里程碑追踪 (核心差异化)
│   │   │   ├── SKILL.md
│   │   │   ├── config.yml
│   │   │   └── scripts/
│   │   │       ├── detector.py
│   │   │       └── celebration.py
│   │   │
│   │   ├── opc-async-task-manager/          # 异步任务 (Legacy)
│   │   │   ├── SKILL.md
│   │   │   ├── config.yml
│   │   │   └── scripts/
│   │   │       ├── scheduler.py
│   │   │       └── executor.py
│   │   │
│   │   └── opc-insight-generator/           # 洞察生成 (核心差异化)
│   │       ├── SKILL.md
│   │       ├── config.yml
│   │       └── scripts/
│   │           └── generator.py
│   │
│   └── opc-remi-lite/                       # ⚠️ 已废弃 (DEPRECATED)
│       ├── SKILL.md
│       └── README.md
│
├── scripts/                                 # 运维脚本
│   ├── setup/                               # 初始化脚本
│   │   └── customer-init.sh                 # ⭐ 客户初始化
│   │
│   ├── deploy/                              # 部署脚本
│   │   ├── deploy-onprem.sh                 # ⭐ 本地部署
│   │   ├── deploy-cloud.sh                  # ⭐ 云端部署
│   │   └── install-skills.sh                # ⭐ Skills 安装
│   │
│   ├── maintenance/                         # 维护脚本
│   │   ├── health-check.sh                  # ⭐ 健康检查
│   │   └── backup-manager.sh                # ⭐ 备份管理
│   │
│   ├── support/                             # 支持脚本
│   │   └── vpn-manager.sh                   # ⭐ VPN 管理
│   │
│   └── recovery/                            # 恢复脚本
│       └── emergency-recovery.sh            # ⭐ 紧急恢复
│
├── config/                                  # 配置模板
│   ├── gateway.yml                          # Gateway 配置
│   ├── gateway-secure.yml                   # 安全加固配置
│   ├── tailscale.yml                        # VPN 配置
│   ├── skills.yml                           # Skills 配置
│   └── security.yml                         # 安全配置
│
├── docs/                                    # 项目文档
│   ├── SCRIPTS.md                           # 脚本使用手册
│   ├── DEPLOYMENT.md                        # 部署指南
│   ├── DEVELOPMENT.md                       # 开发指南
│   ├── SECURITY.md                          # 安全指南
│   ├── API.md                               # API 文档
│   └── USER_MANUAL.md                       # 用户手册
│
├── examples/                                # 示例文件
│   ├── customer-config-example.yml          # 客户配置示例
│   ├── journal-entry-example.yml            # 日志条目示例
│   └── milestone-definition-example.yml     # 里程碑定义示例
│
├── security/                                # 安全相关
│   └── tailscale-acl.yml                    # VPN 访问控制
│
├── monitoring/                              # 监控配置
│   ├── prometheus.yml                       # Prometheus 配置
│   └── grafana-dashboard.json               # Grafana 仪表板
│
├── templates/                               # 模板文件
│   ├── journal-entry-template.yml
│   ├── milestone-template.yml
│   └── report-template.md
│
└── memory/                                  # 项目记忆（内部）
    └── 2026-03-21.md                        # 每日记录
```

---

## 开发工作流

### 1. 本地开发

```bash
# 安装依赖
make install-dev

# 运行测试
make test              # 所有测试
make test-unit         # 仅单元测试
make test-integration  # 仅集成测试
make coverage          # 覆盖率报告

# 代码质量
make lint              # 代码检查
make format            # 格式化
make type-check        # 类型检查
make security          # 安全扫描
make pre-commit        # 提交前检查

# Docker
make docker-build-test # 构建测试镜像
make docker-test       # Docker 中运行测试
make docker-run-prod   # 运行生产环境
```

### 2. 测试驱动开发（TDD）

```
红 → 绿 → 重构
│     │      │
│     │      └── 优化代码结构
│     └───────── 实现功能使测试通过
└─────────────── 编写失败的测试
```

**TDD 目录对应:**
```
tests/unit/           → 开发阶段持续运行
tests/integration/    → 功能完成后运行
tests/e2e/            → 发布前运行
```

### 3. CI/CD 流水线

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Push   │───▶│   CI    │───▶│ Staging │───▶│Production│
│ to Git  │    │  Test   │    │ Deploy  │    │ Deploy  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
      │              │              │              │
      │              │              │              │
      ▼              ▼              ▼              ▼
  Trigger      Unit/Integ      Auto on        Tag push
                + E2E         develop        v*.*.*
```

**工作流文件:**
- `.github/workflows/ci.yml` - push/PR 时触发
- `.github/workflows/security-audit.yml` - 每天凌晨2点
- `.github/workflows/deploy-staging.yml` - develop 分支
- `.github/workflows/deploy-production.yml` - v* 标签

---

## 关键路径说明

### 1. 应用代码路径
```
src/
├── journal/          # 日志核心功能
├── security/         # 数据保险箱和加密
├── patterns/         # 行为分析
├── tasks/            # 异步任务
└── insights/         # 洞察生成
```

### 2. 测试路径
```
tests/
├── unit/             # 隔离测试，快速反馈
├── integration/      # 模块间协作测试
└── e2e/              # 完整用户场景测试
```

### 3. Skills 开发路径
```
skills/opc-{name}/
├── SKILL.md          # Skill 定义（必须）
├── config.yml        # 默认配置
└── scripts/          # 执行脚本（必须）
    └── *.py
```

### 4. 配置路径
```
config/
├── gateway.yml       # Gateway 基础配置
├── gateway-secure.yml # 安全加固配置
├── tailscale.yml     # VPN 网络配置
├── skills.yml        # Skills 加载配置
└── security.yml      # 数据分级和保险箱
```

### 5. 运维脚本路径
```
scripts/
├── setup/            # 初始化
├── deploy/           # 部署
├── maintenance/      # 维护
├── support/          # 支持
└── recovery/         # 恢复
```

---

## 文档读取顺序

```
1. README.md              # 项目概览
2. SYSTEM.md              # 架构设计
3. STRUCTURE.md           # 本文件（了解结构）
4. docs/DEPLOYMENT.md     # 部署指南
5. docs/DEVELOPMENT.md    # 开发指南
6. docs/SECURITY.md       # 安全指南
7. KNOWLEDGE_BASE.md      # 知识库
```

---

## 文件大小预估

| 目录 | 预估大小 | 说明 |
|------|---------|------|
| `src/` | ~50 KB | Python 核心代码 |
| `tests/` | ~100 KB | 测试代码 |
| `skills/` | ~200 KB | Skills 代码 + 文档 |
| `scripts/` | ~100 KB | Bash 脚本 |
| `docs/` | ~200 KB | Markdown 文档 |
| `config/` | ~20 KB | YAML 配置 |
| **总计** | **~670 KB** | 不含 Git 历史 |

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 框架 | OpenClaw Gateway |
| 数据库 | SQLite + Qdrant |
| 网络 | Tailscale VPN |
| 容器 | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| 测试 | pytest + coverage |
| 代码质量 | Black + isort + mypy + pylint |
| 安全 | bandit + safety + detect-secrets |

---

## 完成状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 文档 | 🟡 | REFACTOR_PLAN 已建立，SYSTEM 架构文档待更新 |
| 架构 | 🟡 | v2.2 → v2.4 重构中 |
| Skills | 🟡 | opc-remi-lite 已废弃，套件从 5 个压缩到 3 个核心 |
| 脚本 | 🟡 | install-skills.sh 已更新，其余待适配新架构 |
| Python 核心 | ✅ | src/ 14个模块 |
| 测试 | ✅ | 12个测试文件，TDD 完成 |
| CI/CD | ✅ | 4个 GitHub Actions 工作流 |
| Docker | 🟡 | 待新增 Dockerfile.allinone 和 docker-compose.cloud.yml |
| 配置 | 🟡 | opc-journal-suite/config.yml 已更新 |
| 代码质量 | ✅ | Black, mypy, pylint, pre-commit |

---

*最后更新: 2026-04-10 (重构中)*
