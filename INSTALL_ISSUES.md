# OPC200 项目启动问题记录与解决方案

**记录时间**: 2026-04-08  
**记录人**: 小陵兰  
**项目**: OPC200 (feat/push-architecture 分支)

---

## 环境信息

| 项目 | 状态 | 备注 |
|------|------|------|
| Python | ✅ 3.12.3 | 可用 |
| pip | ✅ 26.0.1 | 已升级 |
| Docker | ❌ 不可用 | 未安装 |
| Docker Compose | ❌ 不可用 | 未安装 |
| 虚拟环境 | ✅ venv 已创建 | 已隔离 |

## 进展更新 (2026-04-08 晚间)

### ✅ 已完成

| 任务 | 状态 | 结果 |
|------|------|------|
| 创建 Python 虚拟环境 | ✅ | venv/ 已创建并隔离 |
| 安装核心依赖 | ✅ | cryptography, numpy, pydantic, pyyaml, click, rich, structlog 已安装 |
| 项目导入测试 | ✅ | `from src import __version__` → "2.2.0" |
| Journal 核心功能 | ✅ | JournalEntry, JournalManager 可正常创建和使用 |

### ⚠️ 仍存在的问题

1. **Qdrant 向量数据库**: 需要 Docker 或本地二进制
2. **ML 依赖**: torch, sentence-transformers 未安装（用于 embeddings）
3. **完整测试**: 部分测试依赖 Qdrant，会失败

### 📊 测试状态

```bash
# 基础导入测试 ✅
python -c "from src import __version__; print(__version__)"  # 2.2.0

# Journal 核心测试 ✅
python -c "from src.journal.core import JournalEntry; e = JournalEntry(content='test')"
```

---

## 原始问题记录


### 现象
```
docker: command not found
docker-compose: command not found
```

### 影响
- 无法使用 docker-compose.minimal.yml 启动服务
- 无法构建 Dockerfile
- 无法运行 Qdrant 向量数据库

### 解决方案选项

**方案 A: 安装 Docker (推荐用于生产环境)**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 安装 Docker Compose
pip install docker-compose
```

**方案 B: 使用纯 Python 运行 (当前采用)**
- 创建 Python 虚拟环境 ✅ 已完成
- 跳过 Docker，直接运行 Python 代码
- 需要替代方案处理 Qdrant 依赖

---

## 问题 2: 依赖安装超时

### 现象
```bash
pip install -e .
# 进程长时间运行，安装 torch/sentence-transformers 等大包超时
```

### 原因
- torch (~2GB) 和 sentence-transformers 安装耗时过长
- 网络不稳定可能导致下载中断

### 解决方案选项

**方案 A: 使用镜像源加速**
```bash
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**方案 B: 分步安装，先装核心依赖**
```bash
# 先安装轻量级依赖
pip install cryptography numpy pydantic pyyaml click rich

# 稍后安装 ML 依赖（或使用 CPU 版本）
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
```

**方案 C: 禁用 ML 功能（最小化运行）**
- 修改 requirements.txt 移除 torch 和 sentence-transformers
- 使用纯文本模式运行 Journal 功能

---

## 问题 3: Qdrant 向量数据库依赖

### 现象
项目依赖 Qdrant 作为向量存储，但 Docker 不可用无法启动 Qdrant 服务。

### 解决方案选项

**方案 A: 安装本地 Qdrant**
```bash
# 下载 Qdrant 二进制
curl -L https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-gnu.tar.gz | tar xz
./qdrant
```

**方案 B: 使用 SQLite 替代 (项目新架构方向)**
根据 README，新架构计划使用 SQLite 替代 Qdrant：
```python
# agent/src/journal/ 使用 SQLite 本地存储
```

**方案 C: 禁用向量功能**
修改配置，使用纯文本搜索替代向量搜索。

---

## 当前可行路径

### 路径 1: 最小化 Python 运行 (推荐先验证)

1. **安装核心依赖** (跳过 ML 大包)
```bash
cd /root/.openclaw/workspace/opc200
source venv/bin/activate
pip install cryptography numpy pydantic pyyaml click rich structlog prometheus-client
```

2. **测试基础模块导入**
```python
python -c "from src import __version__; print(f'OPC200 v{__version__}')"
```

3. **运行单元测试**
```bash
pytest tests/unit -v --tb=short 2>&1 | head -50
```

### 路径 2: 安装 Docker 后完整部署

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动最小化服务
cd /root/.openclaw/workspace/opc200
docker-compose -f docker-compose.minimal.yml up -d
```

### 路径 3: 专注新架构 Agent 开发

根据 README，项目正在迁移到新架构：
```
agent/          # 新架构用户端
platform/       # 新架构平台端
src/            # 旧架构（待迁移）
```

可以直接进入 `agent/` 目录开发新组件，不依赖旧的 docker-compose。

---

## 明日讨论建议

1. **确认运行方式**：Docker 全功能 vs Python 最小化 vs 新架构开发
2. **优先级确认**：P0 任务 (Dockerfile、exporter) 是否需要先解决 Docker 环境
3. **开发方向**：是完善旧架构，还是直接开发新架构的 Agent/Platform 组件

---

## 参考链接

- [OPC200 README](README.md) - 架构说明
- [agent/README.md](agent/README.md) - 新架构 Agent 文档
- [docker-compose.minimal.yml](docker-compose.minimal.yml) - 最小化部署配置
