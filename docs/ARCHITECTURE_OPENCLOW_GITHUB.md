# OPC200 架构重构方案：OpenClaw + GitHub 模式

## 核心洞察：ClawHub.ai 的成功模式

ClawHub 的核心创新在于：
1. **Skill 即文本**：不是二进制插件，而是 Markdown 指令文档
2. **GitHub 即 Registry**：代码托管天然支持版本控制、协作、发布
3. **CLI 即入口**：简单的命令行工具完成搜索/安装/发布
4. **向量搜索**：语义匹配取代关键词搜索
5. **分层架构**：Workspace → Managed → Bundled 三级技能体系

---

## OPC200 的重新定位

### 现状问题
当前 OPC200 是一个**单体应用**：
- 所有功能耦合在一起
- 部署复杂（Docker、K8s）
- 升级困难
- 定制化能力弱

### 新模式：OPC200 as a Skill Ecosystem

借鉴 ClawHub，将 OPC200 重构为 **"技能化的 One Person Company 操作系统"**：

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPC200 生态系统                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│   │   GitHub     │    │   OpenClaw   │    │   OPC200     │    │
│   │   Registry   │◄──►│   Gateway    │◄──►│   Core       │    │
│   │              │    │              │    │   Service    │    │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              OPC200 Skills (GitHub Repos)                │  │
│   ├─────────────────────────────────────────────────────────┤  │
│   │  opc-journal-core          coidea/opc-journal-core      │  │
│   │  opc-pattern-recognition   coidea/opc-pattern-recognition│ │
│   │  opc-milestone-tracker     coidea/opc-milestone-tracker │  │
│   │  opc-async-task-manager    coidea/opc-async-task-manager│  │
│   │  opc-insight-generator     coidea/opc-insight-generator │  │
│   │  opc-billing               coidea/opc-billing           │  │
│   │  opc-customer-support      coidea/opc-customer-support  │  │
│   │  opc-analytics             coidea/opc-analytics         │  │
│   │  ... (第三方 Skills)                                      │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 架构分层详解

### Layer 1: GitHub Registry Layer

**功能**：代码托管、版本控制、协作、发布

```yaml
# 每个 OPC200 Skill 是一个 GitHub Repository
repo: coidea/opc-journal-core
structure:
  - SKILL.md          # 技能定义文档 (类似 Dockerfile)
  - scripts/          # 可选的执行脚本
    - record.py
    - search.py
  - tests/            # 测试用例
  - .github/
    - workflows/      # CI/CD
      - test.yml
      - publish.yml
  - README.md
  - LICENSE
```

**GitHub 提供的天然能力**：
- ✅ 版本控制 (git)
- ✅ 发布管理 (GitHub Releases)
- ✅ 协作 (Issues, PRs, Discussions)
- ✅ CI/CD (GitHub Actions)
- ✅ 权限管理 (Collaborators, Teams)
- ✅ 免费托管 (Public repos)

---

### Layer 2: OpenClaw Gateway Layer

**功能**：Agent 运行时、技能加载、任务调度

```yaml
# OpenClaw 配置
openclaw:
  skills:
    sources:
      - type: github
        org: coidea
        auto_sync: true
      - type: clawhub
        query: "opc-*"
  
  agents:
    - name: journal-agent
      skills:
        - opc-journal-core
        - opc-pattern-recognition
      
    - name: milestone-agent
      skills:
        - opc-milestone-tracker
      
    - name: insight-agent
      skills:
        - opc-insight-generator
```

**OpenClaw 负责**：
- Skill 发现与加载
- Agent 生命周期管理
- 任务路由与调度
- 记忆管理 (MEMORY.md)
- 多渠道接入 (Telegram, Feishu, etc.)

---

### Layer 3: OPC200 Core Service Layer

**功能**：业务核心、数据持久化、多租户管理

这是 OPC200 区别于普通 OpenClaw 安装的核心价值所在：

```python
# opc200/core/service.py
class OPC200Core:
    """One Person Company 核心服务"""
    
    def __init__(self):
        self.customer_manager = CustomerManager()
        self.data_vault = DataVault()  # 加密存储
        self.billing = BillingService()
        self.analytics = AnalyticsService()
    
    async def onboard_customer(self, customer_id: str):
        """新客户入驻"""
        # 1. 创建客户空间
        # 2. 安装默认 skills
        # 3. 初始化数据存储
        # 4. 设置默认 Agent 配置
        pass
    
    async def process_journal_entry(self, customer_id: str, entry: dict):
        """处理日志条目"""
        # 1. 存储到客户专属空间
        # 2. 触发模式识别
        # 3. 检测里程碑
        # 4. 生成洞察
        pass
```

**核心服务组件**：

| 组件 | 功能 | 技术选型 |
|------|------|----------|
| Customer Manager | 多租户管理 | PostgreSQL + 行级安全 |
| Data Vault | 加密数据存储 | SQLite (本地) / PostgreSQL (云端) |
| Skill Registry | Skill 元数据管理 | GitHub API + 本地缓存 |
| Billing | 计费与订阅 | Stripe API |
| Analytics | 使用分析 | ClickHouse / PostgreSQL |
| Notification | 多渠道通知 | n8n / 自建 |

---

## Skill 设计规范 (参考 ClawHub)

### SKILL.md 结构

```markdown
---
name: opc-journal-core
description: OPC200 核心日志技能 - 记录、查询、导出用户旅程
version: 1.2.0
author: coidea
metadata:
  requires:
    env:
      - OPC200_API_KEY
      - CUSTOMER_ID
    bins:
      - python3
    skills:
      - opc-data-vault  # 依赖其他 skill
  tags:
    - journal
    - logging
    - opc200
    - core
  pricing: free  # free | pro | enterprise
---

# OPC Journal Core Skill

## 何时使用

当用户需要：
- 记录工作日志
- 查询历史记录
- 导出周报/月报

## 工作流

### 记录日志

1. 接收用户输入
2. 生成 Entry ID (JE-{YYYYMMDD}-{UUID})
3. 调用 `opc-data-vault` 存储
4. 返回确认消息

### 查询日志

1. 解析查询条件 (时间范围、关键词)
2. 调用 Data Vault 搜索
3. 格式化返回结果

## 错误处理

- 存储失败：重试 3 次，失败后通知用户
- 权限不足：提示升级订阅计划

## 示例

用户："记录今天的进度"
→ 创建条目 JE-20260327-A1B2C3
→ 存储到 Data Vault
→ 返回："已记录，Entry ID: JE-20260327-A1B2C3"
```

---

## CLI 工具设计 (opc CLI)

```bash
# 安装 OPC200 CLI
npm install -g opc

# 客户入驻
opc onboard --customer-id OPC-001

# 安装技能 (从 GitHub)
opc skills install coidea/opc-journal-core
opc skills install coidea/opc-pattern-recognition

# 安装技能 (从 ClawHub)
opc skills install opc-journal-core  # 自动解析为 coidea/opc-journal-core

# 搜索技能
opc skills search "里程碑"

# 更新技能
opc skills update --all

# 启动 Agent
opc agent start --config ./opc-config.yml

# 查看客户数据
opc data export --customer-id OPC-001 --format markdown

# 发布技能 (开发者)
opc publish --path ./my-skill --org coidea
```

---

## 数据流架构

```
用户 (Telegram/Feishu/Slack)
    │
    ▼
OpenClaw Gateway
    │
    ├──► Agent 1 (journal-agent)
    │       ├──► Skill: opc-journal-core
    │       │       ├──► 调用 Data Vault API
    │       │       │       └──► PostgreSQL (加密存储)
    │       │       └──► 返回结果
    │       └──► Skill: opc-pattern-recognition
    │
    ├──► Agent 2 (milestone-agent)
    │       └──► Skill: opc-milestone-tracker
    │               └──► 检测里程碑 → 触发庆祝
    │
    └──► Agent 3 (insight-agent)
            └──► Skill: opc-insight-generator
                    └──► 生成洞察 → 推送通知
```

---

## 部署模式

### 模式 1: 本地部署 (隐私优先)

```yaml
# docker-compose.local.yml
services:
  openclaw:
    image: openclaw/openclaw:latest
    volumes:
      - ./skills:/app/skills
      - ./data:/app/data
  
  opc200-core:
    image: coidea/opc200-core:latest
    environment:
      - DEPLOYMENT_MODE=local
      - DATA_PATH=/data
    volumes:
      - ./customer-data:/data
  
  postgres:
    image: postgres:15
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
```

**特点**：
- 所有数据本地存储
- 无需网络连接 (除 GitHub 拉取 skills)
- 适合极度隐私敏感用户

### 模式 2: 云端托管 (便捷优先)

```yaml
# docker-compose.cloud.yml
services:
  openclaw-gateway:
    image: openclaw/openclaw:latest
    
  opc200-core:
    image: coidea/opc200-core:latest
    environment:
      - DEPLOYMENT_MODE=cloud
      - DATABASE_URL=postgresql://... (RDS)
      - REDIS_URL=redis://... (ElastiCache)
```

**特点**：
- 数据加密存储在云端
- 自动备份、高可用
- 订阅制收费

### 模式 3: 混合部署 (默认推荐)

```yaml
# 敏感数据本地，非敏感云端
services:
  openclaw:
    image: openclaw/openclaw:latest
    
  opc200-core:
    image: coidea/opc200-core:latest
    environment:
      - DEPLOYMENT_MODE=hybrid
      - JOURNAL_STORAGE=local  # 日志本地存储
      - ANALYTICS_STORAGE=cloud  # 分析数据云端
```

---

## 与 ClawHub.ai 的差异

| 维度 | ClawHub.ai | OPC200 |
|------|------------|--------|
| **定位** | 通用 Skill 市场 | 垂直领域 (One Person Company) |
| **Skill 来源** | 社区贡献 | 官方 + 认证第三方 |
| **数据** | 无中心存储 | 客户数据隔离存储 |
| **计费** | 免费 | Freemium (基础免费，高级付费) |
| **部署** | 纯云端 | 本地/云端/混合 |
| **Agent** | 单一 Agent | 多 Agent 协作 |

---

## 实施路线图

### Phase 1: 基础架构 (2 周)
- [ ] 创建 `opc` CLI 工具
- [ ] 实现 GitHub Registry 集成
- [ ] 重构现有 5 个 Skills 到独立 GitHub repos
- [ ] 实现 OPC200 Core Service 基础框架

### Phase 2: 多租户 (2 周)
- [ ] 实现 Customer Manager
- [ ] 实现 Data Vault (加密存储)
- [ ] 实现订阅计费系统
- [ ] 权限与隔离

### Phase 3: 生态扩展 (持续)
- [ ] 开放第三方 Skill 开发
- [ ] Skill 认证体系
- [ ] Marketplace (类似 ClawHub)
- [ ] 文档与教程

---

## 关键技术决策

### 1. 为什么选择 GitHub 而不是自建 Registry？

**优点**：
- ✅ 免费 (Public repos)
- ✅ 成熟的基础设施
- ✅ 开发者熟悉
- ✅ 天然支持版本控制
- ✅ CI/CD 集成

**缺点**：
- ❌ 依赖外部服务
- ❌ 国内访问可能不稳定

**缓解方案**：
- 国内镜像 (Gitee/Codeup)
- 本地缓存机制

### 2. Skill 版本管理

采用 **SemVer + Git Tags**：

```bash
# Skill repo
git tag -a v1.2.0 -m "Add async export feature"
git push origin v1.2.0

# OPC CLI 安装特定版本
opc skills install coidea/opc-journal-core@1.2.0
```

### 3. 数据安全

- 本地部署：数据完全不出境
- 云端部署：AES-256 加密，客户持有密钥
- 传输：TLS 1.3

---

## 总结

通过借鉴 ClawHub.ai 的架构模式，OPC200 可以：

1. **降低部署复杂度**：从单体应用变为可组合的技能集
2. **提高可扩展性**：第三方可以开发自己的 OPC200 Skills
3. **增强定制化**：用户按需安装技能，避免功能膨胀
4. **复用生态**：直接利用 GitHub 的协作与版本控制能力
5. **商业模式清晰**：Freemium + 企业版订阅

**核心价值主张**：
> "OPC200 是 One Person Company 的 OpenClaw 发行版"
> 
> —— 预装了完整的创业辅助技能集，开箱即用

---

*思考时间: 2026-03-27*
*参考: clawhub.ai architecture, OpenClaw documentation*