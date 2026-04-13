# OPC200 开发指南

> **版本**: 2.2.0  
> **适用**: OPC200 开发者、Skill 开发者

## 目录

1. [开发环境](#开发环境)
2. [项目结构](#项目结构)
3. [核心模块](#核心模块)
4. [开发 Skill](#开发-skill)
5. [测试](#测试)
6. [贡献指南](#贡献指南)

---

## 开发环境

### 前置要求

- Python 3.11+
- Poetry (推荐) 或 pip
- Docker & Docker Compose
- Git

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/coidea-ai/OPC200.git
cd OPC200

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装 pre-commit hooks
pre-commit install
```

### 使用 Poetry（推荐）

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 激活环境
poetry shell
```

---

## 项目结构

```
opc200/
├── src/                    # Python 核心模块
│   ├── journal/           # 日志系统
│   ├── security/          # 安全模块
│   ├── patterns/          # 模式分析
│   ├── tasks/             # 任务调度
│   └── insights/          # 洞察生成
│
├── skills/                # OpenClaw Skills
│   └── opc-journal/           # OPC Journal 单一 CLI Skill
│
├── config/                # 配置文件
│   ├── gateway.yml
│   ├── tailscale.yml
│   ├── skills.yml
│   └── security.yml
│
├── scripts/               # 运维脚本
│   ├── setup/
│   ├── deploy/
│   └── maintenance/
│
├── tests/                 # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/                  # 文档
```

---

## 核心模块

### Journal 模块

```python
from src.journal import JournalCore, JournalEntry

# 初始化
journal = JournalCore("/data/journal.db")

# 记录条目
entry = await journal.record(
    content="今日完成登录功能开发",
    entry_type="action",
    tags=["开发", "登录"],
    metadata={"project": "auth-service"}
)

# 查询
entries = await journal.query(
    start_time=datetime.now() - timedelta(days=7),
    entry_types=["action", "milestone"],
    tags=["开发"]
)
```

### Security 模块

```python
from src.security import SecureVault, VaultKeyManager

# 初始化保险箱
key_manager = VaultKeyManager.from_password("secure_password")
vault = SecureVault("/data/vault", key_manager)

# 存储凭证（Agent 只能看到元数据）
cred_id = vault.store_credential(
    name="openai_api_key",
    credential_type="api_key",
    value="sk-...",
    metadata={"service": "openai"}
)

# 服务层解密（需要授权）
value = vault.decrypt_for_service(cred_id, service_auth_token)
```

### Pattern 模块

```python
from src.patterns import PatternAnalyzer

# 初始化
analyzer = PatternAnalyzer("/data/patterns.db")

# 生成画像
profile = analyzer.generate_full_profile(
    user_id="user-001",
    journal_entries=entries
)

# 获取时间模式
time_patterns = analyzer.analyze_time_patterns(entries)
```

### Task 模块

```python
from src.tasks import TaskScheduler, TaskPriority

# 初始化
scheduler = TaskScheduler("/data/tasks.db")

# 注册处理器
async def my_handler(payload):
    # 处理逻辑
    return {"status": "ok"}

scheduler.register_handler("my_task", my_handler)

# 提交任务
task = await scheduler.submit(
    name="my_task",
    description="示例任务",
    payload={"key": "value"},
    priority=TaskPriority.HIGH
)
```

---

## 开发 Skill

### Skill 结构

```
skills/my-skill/
├── SKILL.md          # Skill 定义
├── config.yml        # 默认配置
└── scripts/
    ├── init.py       # 初始化
    └── main.py       # 主逻辑
```

### SKILL.md 模板

```markdown
# My Skill

## Description
技能描述

## Usage
\`\`\`bash
clawhub run my-skill
\`\`\`

## Configuration
\`\`\`yaml
my_skill:
  option: value
\`\`\`

## Permissions
- file:read:${OPC200_DATA_DIR}
- network:outbound:api.example.com
```

### 示例 Skill

```python
# skills/my-skill/scripts/main.py
import sys
import json

def main():
    # 读取配置
    config = json.loads(sys.argv[1])
    
    # 执行业务逻辑
    result = process(config)
    
    # 输出结果
    print(json.dumps(result))

def process(config):
    # 实现逻辑
    return {"status": "success"}

if __name__ == "__main__":
    main()
```

---

## 测试

### 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 覆盖率
pytest --cov=src --cov-report=html

# 所有测试
pytest
```

### 测试示例

```python
# tests/unit/test_journal.py
import pytest
from src.journal import JournalCore

@pytest.fixture
async def journal(tmp_path):
    db_path = tmp_path / "test.db"
    return JournalCore(str(db_path))

@pytest.mark.asyncio
async def test_record_entry(journal):
    entry = await journal.record(
        content="测试内容",
        entry_type="thought"
    )
    
    assert entry.content == "测试内容"
    assert entry.entry_type == "thought"
    
    # 验证存储
    retrieved = await journal.get(entry.id)
    assert retrieved is not None
```

---

## 贡献指南

### 提交 PR

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8
- 使用 Black 格式化代码
- 添加类型提示
- 编写文档字符串

```bash
# 格式化
black src/ tests/

# 类型检查
mypy src/

# 代码检查
flake8 src/
```

### 文档

- 更新 README.md
- 更新相关文档
- 添加代码注释

---

## 发布

### 版本管理

遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/):

- MAJOR: 不兼容的 API 修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的问题修正

### 发布流程

```bash
# 1. 更新版本号
# 更新 __init__.py 和 pyproject.toml

# 2. 更新 CHANGELOG.md

# 3. 创建标签
git tag -a v2.2.0 -m "Release version 2.2.0"
git push origin v2.2.0

# 4. 构建和发布
poetry build
poetry publish
```

---

## 参考

- [API 文档](./API.md)
- [架构设计](../SYSTEM.md)
- [部署指南](./DEPLOYMENT.md)
