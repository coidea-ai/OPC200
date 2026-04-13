# OPC200 目录结构改造说明

## 改造日期
2026年4月9日

## 分支
`feat/push-architecture`

## 改造背景

根据架构改进方案，从私有化全容器部署转向 **Push 模式集中监控架构**。

核心变化：
- 明确区分**平台侧**（云端）和**用户侧**（Agent）
- 用户端从 5 容器精简为单一 Agent
- 平台端集中处理监控、告警、版本管理

## 新目录结构

```
opc-200/
├── README.md
├── Makefile
├── pyproject.toml
│
├── agent/                    # 📦 用户侧（NEW）
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── src/
│   │   ├── gateway/         # 精简版 Gateway（NEW）
│   │   ├── journal/         # 本地存储（从 src/ 复制）
│   │   ├── exporter/        # 指标推送（NEW）
│   │   ├── selfhealer/      # 自修复机制（NEW）
│   │   ├── updater/         # 版本更新（NEW）
│   │   ├── security/        # 安全模块（从 src/ 复制）
│   │   ├── utils/           # 工具模块（从 src/ 复制）
│   │   └── tasks/           # 任务调度（从 src/ 复制）
│   ├── config/              # 配置文件（从 config/ 复制）
│   ├── skills/              # Skills（从 skills/ 复制）
│   └── scripts/             # 安装脚本
│
├── platform/                 # 📦 平台侧（NEW）
│   ├── README.md
│   ├── docker-compose.yml
│   ├── pushgateway/         # 指标接收（NEW）
│   ├── prometheus/          # 时序存储
│   ├── grafana/             # 可视化
│   ├── alertmanager/        # 告警路由
│   └── version-control/     # 版本管理（NEW）
│
├── shared/                   # 🔗 共享组件（NEW）
│   ├── proto/               # 通信协议
│   ├── pkg/                 # 共享工具包
│   └── config/              # 共享配置结构
│
├── docs/                     # 📚 文档（NEW）
│   ├── architecture/        # 架构文档
│   ├── deployment/          # 部署指南
│   └── api/                 # API 文档
│
├── scripts/                  # 🔧 工具脚本
│   ├── dev/                 # 开发脚本
│   ├── ci/                  # CI/CD 脚本
│   └── migration/           # 数据迁移脚本
│
└── tests/                    # 🧪 测试
    ├── platform/            # 平台侧测试
    ├── agent/               # Agent 测试
    └── e2e/                 # 端到端测试
```

## 旧目录状态

以下目录/文件保持原样，**标记为旧结构**，后续逐步迁移或删除：n

| 旧路径 | 状态 | 说明 |
|--------|------|------|
| `src/` | ⚠️ 旧结构 | 原代码已复制到 `agent/src/`，需调整 import 后删除 |
| `skills/` | ⚠️ 旧结构 | 已复制到 `agent/skills/`，后续删除 |
| `config/` | ⚠️ 旧结构 | 已复制到 `agent/config/`，后续删除 |
| `monitoring/` | ⚠️ 旧结构 | Prometheus/Grafana 配置已移动到 `platform/` |
| `Dockerfile` | ⚠️ 旧文件 | 原完整镜像构建文件 |
| `Dockerfile.gateway` | ⚠️ 旧文件 | 原 Gateway 构建文件，参考用于 `agent/src/gateway/` |
| `docker-compose.yml` | ⚠️ 旧文件 | 原 5 服务编排文件，参考用于 `agent/` 和 `platform/` |

## 文件迁移清单

### 已复制到新目录的文件

```
# Agent 侧
src/journal/*         → agent/src/journal/
src/security/*        → agent/src/security/
src/utils/*           → agent/src/utils/
src/tasks/*           → agent/src/tasks/
src/exceptions.py     → agent/src/
src/__init__.py       → agent/src/
src/insights/*        → agent/src/journal/ (合并)
src/patterns/*        → agent/src/journal/ (合并)

skills/*              → agent/skills/
config/*              → agent/config/
Dockerfile.gateway    → agent/src/gateway/ (参考)
docker-compose.minimal.yml → agent/ (参考)

# Platform 侧
monitoring/prometheus/* → platform/prometheus/
monitoring/grafana/*    → platform/grafana/
docker-compose.yml      → platform/ (参考)

# 新增文件（占位）
agent/src/exporter/README.md
agent/src/selfhealer/README.md
agent/src/updater/README.md
agent/src/gateway/README.md
agent/README.md
platform/README.md
shared/README.md
```

### 待处理事项

- [ ] 调整 `agent/src/` 中的 import 语句（`from src.xxx` → 相对导入或新包名）
- [ ] 创建 `agent/Dockerfile` 单容器构建文件
- [ ] 创建 `platform/docker-compose.yml` 平台服务编排
- [ ] 实现 `exporter/` 指标推送模块
- [ ] 实现 `selfhealer/` 自修复模块
- [ ] 实现 `updater/` 版本更新模块
- [ ] 迁移完成后删除旧目录（`src/`, `skills/`, `config/` 等）

## 引用调整说明

### Python Import 变化

```python
# 旧方式（需修改）
from src.journal import JournalManager
from src.security import EncryptionService

# 新方式选项 1：保持 src 包名（需调整 pyproject.toml）
from src.journal import JournalManager  # 不变，但包路径改为 agent/src/

# 新方式选项 2：改为 opc200 包名（推荐）
from opc200.journal import JournalManager

# 新方式选项 3：相对导入（Agent 内部模块）
from .journal import JournalManager
```

### Docker 构建变化

```dockerfile
# 旧 Dockerfile
copy src/ ./src/
copy skills/ ./skills/

# 新 Dockerfile（在 agent/ 目录下）
copy src/ ./src/
copy skills/ ./skills/
copy config/ ./config/

# 如果需要引用 shared/，从根目录构建
copy shared/proto/ ./shared/proto/
```

## 后续步骤

1. 完善 `agent/Dockerfile` 单容器构建
2. 完善 `platform/docker-compose.yml` 平台编排
3. 实现 Exporter、Self-Healer、Updater 模块
4. 调整 import 路径并测试
5. 删除旧目录，完成迁移

## 参考资料

- `docs/architecture/opc200_architecture_report_v2.md` - 架构改进方案
