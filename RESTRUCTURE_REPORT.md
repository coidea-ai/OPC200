# OPC200 目录结构改造报告

## 执行摘要

✅ 已完成从 `main` 分支创建 `feat/push-architecture` 分支  
✅ 已完成新目录结构创建和文件复制  
✅ 旧文件保持原样（未删除，便于对照）

---

## 一、分支信息

- **源分支**: `main`
- **新分支**: `feat/push-architecture`
- **当前位置**: `/root/.openclaw/storage/projects/opc-200`

---

## 二、新目录结构总览

```
opc-200/
├── agent/                    # 📦 用户侧（新增）
│   ├── src/
│   │   ├── gateway/         # 精简版 Gateway（新增 README）
│   │   ├── journal/         # 本地存储（从 src/ 复制）
│   │   ├── exporter/        # 指标推送（新增 README + __init__）
│   │   ├── selfhealer/      # 自修复机制（新增 README + __init__）
│   │   ├── updater/         # 版本更新（新增 README + __init__）
│   │   ├── security/        # 安全模块（从 src/ 复制）
│   │   ├── utils/           # 工具模块（从 src/ 复制）
│   │   └── tasks/           # 任务调度（从 src/ 复制）
│   ├── config/              # 配置文件（从 config/ 复制，6个文件）
│   ├── skills/              # Skills（从 skills/ 复制，76个文件）
│   ├── scripts/             # 安装脚本（目录创建）
│   └── README.md            # Agent 说明文档（新增）
│
├── platform/                 # 📦 平台侧（新增）
│   ├── pushgateway/         # 指标接收服务（目录创建）
│   ├── prometheus/          # 时序存储（从 monitoring/ 复制）
│   ├── grafana/             # 可视化（从 monitoring/ 复制）
│   ├── alertmanager/        # 告警路由（目录创建）
│   ├── version-control/     # 版本管理（目录创建）
│   ├── docker-compose.yml   # 从根目录复制（参考）
│   └── README.md            # 平台说明文档（新增）
│
├── shared/                   # 🔗 共享组件（新增）
│   ├── proto/               # 通信协议（目录创建）
│   ├── pkg/                 # 共享工具包（目录创建）
│   ├── config/              # 共享配置结构（目录创建）
│   └── README.md            # 共享组件说明（新增）
│
├── docs/                     # 📚 文档（新增）
│   ├── architecture/        # 架构文档
│   │   └── DIRECTORY_MIGRATION.md  # 迁移说明（新增）
│   ├── deployment/          # 部署指南（目录创建）
│   └── api/                 # API 文档（目录创建）
│
└── [原有文件和目录保持不动]  # ⚠️ 旧结构保留
```

---

## 三、具体改动清单

### 1. 创建的新目录（共 20+ 个）

| 路径 | 说明 |
|------|------|
| `agent/` | 用户侧根目录 |
| `agent/src/` | Agent 源代码 |
| `agent/src/gateway/` | 精简 Gateway |
| `agent/src/journal/` | 本地存储模块 |
| `agent/src/exporter/` | 指标推送模块 |
| `agent/src/selfhealer/` | 自修复模块 |
| `agent/src/updater/` | 版本更新模块 |
| `agent/config/` | 配置文件 |
| `agent/skills/` | Skills |
| `agent/scripts/` | 安装脚本 |
| `platform/` | 平台侧根目录 |
| `platform/pushgateway/` | 指标接收 |
| `platform/prometheus/` | 时序存储 |
| `platform/grafana/` | 可视化 |
| `platform/alertmanager/` | 告警路由 |
| `platform/version-control/` | 版本管理 |
| `shared/` | 共享组件 |
| `docs/architecture/` | 架构文档 |
| `docs/deployment/` | 部署文档 |
| `docs/api/` | API 文档 |

### 2. 复制/迁移的文件

| 来源 | 目标 | 文件数 | 说明 |
|------|------|--------|------|
| `src/journal/` | `agent/src/journal/` | 4个 | 日志核心模块 |
| `src/security/` | `agent/src/security/` | 2个 | 安全模块 |
| `src/utils/` | `agent/src/utils/` | 3个 | 工具模块 |
| `src/tasks/` | `agent/src/tasks/` | 2个 | 任务调度 |
| `src/insights/` | `agent/src/journal/` | - | 合并到 journal |
| `src/patterns/` | `agent/src/journal/` | - | 合并到 journal |
| `src/exceptions.py` | `agent/src/` | 1个 | 异常定义 |
| `src/__init__.py` | `agent/src/` | 1个 | 包初始化 |
| `skills/` | `agent/skills/` | 76个 | Skills 完整复制 |
| `config/` | `agent/config/` | 6个 | 配置文件 |
| `monitoring/prometheus/` | `platform/prometheus/` | 2个 | Prometheus 配置 |
| `monitoring/grafana/` | `platform/grafana/` | 1个 | Dashboard 配置 |
| `Dockerfile.gateway` | `agent/src/gateway/` | 1个 | 参考用 |
| `docker-compose.yml` | `platform/` | 1个 | 参考用 |
| `docker-compose.minimal.yml` | `agent/` | 1个 | 参考用 |

**总计**: 约 100+ 个文件已复制到新目录

### 3. 新增的文件（共 11 个）

| 文件路径 | 类型 | 说明 |
|----------|------|------|
| `agent/README.md` | 文档 | Agent 使用说明 |
| `agent/src/gateway/README.md` | 文档 | Gateway 模块说明 |
| `agent/src/gateway/__init__.py` | Python | 包初始化 |
| `agent/src/exporter/README.md` | 文档 | Exporter 模块说明 |
| `agent/src/exporter/__init__.py` | Python | 包初始化 |
| `agent/src/selfhealer/README.md` | 文档 | SelfHealer 模块说明 |
| `agent/src/selfhealer/__init__.py` | Python | 包初始化 |
| `agent/src/updater/README.md` | 文档 | Updater 模块说明 |
| `agent/src/updater/__init__.py` | Python | 包初始化 |
| `platform/README.md` | 文档 | 平台侧说明 |
| `shared/README.md` | 文档 | 共享组件说明 |
| `docs/architecture/DIRECTORY_MIGRATION.md` | 文档 | 完整迁移说明 |

---

## 四、旧目录状态

以下目录/文件 **保持原样**，未做任何修改或删除：

```
src/                    # 原代码目录（仍保留）
skills/                 # 原 Skills 目录（仍保留）
config/                 # 原配置目录（仍保留）
monitoring/             # 原监控目录（仍保留）
Dockerfile              # 原构建文件（仍保留）
Dockerfile.gateway      # 原 Gateway 文件（仍保留）
docker-compose.yml      # 原编排文件（仍保留）
tests/                  # 原测试目录（仍保留）
scripts/                # 原脚本目录（仍保留）
```

> ⚠️ 这些旧目录后续会逐步迁移或删除，目前保留用于对照和回退。

---

## 五、待办事项（下一步工作）

### 高优先级

- [ ] **创建 `agent/Dockerfile`** - 单容器构建 Agent
- [ ] **创建 `platform/docker-compose.yml`** - 平台服务编排
- [ ] **调整 Python import 路径** - `from src.xxx` → 新包名或相对导入
- [ ] **实现 `exporter/push_exporter.py`** - 指标推送核心逻辑
- [ ] **实现 `selfhealer/l1_local_fix.py`** - L1 自修复逻辑

### 中优先级

- [ ] **实现 `updater/update_client.py`** - 版本更新客户端
- [ ] **创建 `shared/proto/` 协议定义** - Agent 与 Platform 通信协议
- [ ] **调整 `pyproject.toml`** - 支持新的包路径
- [ ] **迁移测试文件** - 将测试按 agent/platform 重新组织

### 低优先级

- [ ] **删除旧目录** - 确认新结构稳定后删除 `src/`, `skills/`, `config/` 等
- [ ] **更新根目录 README.md** - 说明新的项目结构
- [ ] **完善 CI/CD 脚本** - 适配新的目录结构

---

## 六、Git 状态

```bash
$ git status

新分支: feat/push-architecture
未跟踪文件: agent/, platform/, shared/, docs/architecture/
已修改: 无（旧文件未动）
```

**未推送到远程**，所有改动仅在本地。

---

## 七、关键文件位置速查

| 要找的内容 | 新位置 |
|------------|--------|
| Agent 代码 | `agent/src/` |
| Agent 配置 | `agent/config/` |
| Agent Skills | `agent/skills/` |
| Platform 监控 | `platform/prometheus/`, `platform/grafana/` |
| 架构文档 | `docs/architecture/DIRECTORY_MIGRATION.md` |
| 原代码（旧） | `src/`（仍保留） |
| 原配置（旧） | `config/`（仍保留） |

---

## 总结

✅ **已完成**: 新目录结构搭建、文件复制、README 文档  
⏳ **待完成**: Dockerfile、import 调整、核心模块实现  
📋 **参考文档**: `docs/architecture/DIRECTORY_MIGRATION.md`

**当前分支**: `feat/push-architecture`（未推送）
