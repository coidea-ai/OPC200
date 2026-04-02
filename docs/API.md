# OPC200 API 文档

## 概述

OPC200 提供两种使用方式：
1. **Python 类库 API** - 直接导入使用（当前主要方式）
2. **RESTful API** - 通过 HTTP 调用（规划中）

**当前版本**: v2.3.0  
**最后更新**: 2026-04-01

---

## Python 类库 API

### 安装

```bash
pip install -e .
```

### 核心模块

#### 1. Journal 模块 (`src.journal`)

##### JournalEntry - 日志条目

```python
from src.journal.core import JournalEntry

# 创建条目
entry = JournalEntry(
    content="今天完成了产品原型的设计",
    tags=["产品设计", "里程碑"],
    metadata={"mood": "productive", "energy_level": 8}
)

# 添加/删除标签
entry.add_tag("重要")
entry.remove_tag("里程碑")

# 检查标签
if entry.has_tag("重要"):
    print("这是重要条目")

# 更新内容
entry.update_content("今天完成了产品原型的设计（修订版）")

# 操作元数据
entry.set_metadata("location", "办公室")
mood = entry.get_metadata("mood", "neutral")
entry.delete_metadata("energy_level")

# 导出
entry_dict = entry.to_dict()
entry_json = entry.to_json()

# 从字典/JSON 重建
entry2 = JournalEntry.from_dict(entry_dict)
entry3 = JournalEntry.from_json(entry_json)
```

##### JournalManager - 日志管理器

```python
import sqlite3
from src.journal.core import JournalManager, JournalEntry

# 初始化（使用内存数据库）
conn = sqlite3.connect(":memory:")
manager = JournalManager(conn)
manager.create_table()

# 创建条目
entry = JournalEntry(content="测试条目")
manager.create_entry(entry)

# 查询条目
entry_id = entry.id
found = manager.get_entry(entry_id)  # 返回 JournalEntry 或 None

# 更新条目
entry.update_content("更新后的内容")
manager.update_entry(entry)

# 删除条目
manager.delete_entry(entry_id)

# 列出租用
entries = manager.list_entries(limit=10, offset=0)

# 按标签筛选
tagged = manager.list_entries_by_tag("重要")

# 搜索内容
results = manager.search_entries("关键词")

# 获取所有标签
all_tags = manager.get_all_tags()

# 标签管理
manager.rename_tag("旧标签", "新标签")
manager.delete_tag("废弃标签")
```

##### VectorStore - 向量存储（语义搜索）

> **依赖要求**: 需要安装 `sentence-transformers` 和 `numpy`
> ```bash
> pip install sentence-transformers numpy
> ```

```python
from src.journal.vector_store import VectorStore

# 初始化（需要 sentence-transformers）
# 首次使用会自动下载嵌入模型（约 100MB）
store = VectorStore(embedding_model="all-MiniLM-L6-v2")

# 添加条目（含向量化）
store.add_entry(entry)

# 语义搜索 - 基于语义相似度而非关键词匹配
similar = store.search_similar("如何提高工作效率", limit=5)
# 返回: List[{"entry": JournalEntry, "score": float}]

# 查找相似条目
related = store.find_similar_to(entry_id, limit=5)
```

**性能注意**: 
- 首次加载模型需要 ~2-5 秒
- 搜索时间随条目数增长，建议定期重建索引

#### 2. Tasks 模块 (`src.tasks`)

##### TaskScheduler - 任务调度器

```python
from src.tasks.scheduler import TaskScheduler, CronParser

scheduler = TaskScheduler()

# 添加定时任务
def my_task():
    print("执行任务")

job_id = scheduler.add_job(
    my_task,
    trigger="cron",
    job_id="daily_report",
    hour=9,
    minute=0
)

# 管理任务
scheduler.pause_job(job_id)
scheduler.resume_job(job_id)
job = scheduler.get_job(job_id)
all_jobs = scheduler.list_jobs()
scheduler.remove_job(job_id)
```

##### CronParser - Cron 表达式解析

```python
from src.tasks.scheduler import CronParser

parser = CronParser()

# 解析 cron 表达式
parsed = parser.parse("0 9 * * 1-5")  # 工作日 9:00

# 验证
cron_valid = parser.validate("0 */6 * * *")

# 计算下次执行时间
from datetime import datetime
next_run = parser.get_next_run("0 9 * * *", from_time=datetime.now())
```

##### TaskQueue - 异步任务队列

```python
from src.tasks.scheduler import TaskQueue
import asyncio

queue = TaskQueue(default_timeout=60)

async def example():
    # 添加任务
    task_id = await queue.enqueue(
        my_async_function,
        priority=5,  # 1-10，数字越小优先级越高
        param1="value1"
    )
    
    # 取消任务
    cancelled = await queue.cancel(task_id)
    
    # 获取队列大小
    size = queue.size()

asyncio.run(example())
```

##### RecurringTask - 循环任务

```python
from src.tasks.scheduler import RecurringTask, CronParser

# 创建循环任务
task = RecurringTask(
    func=my_function,
    cron="0 9 * * *",  # 每天 9:00
    task_id="morning_routine"
)

# 检查是否到期
if task.is_due():
    # 执行并记录
    success = execute_task()
    task.record_execution(success)
    
    # 获取下次执行时间
    next_run = task.get_next_run()
```

#### 3. Insights 模块 (`src.insights`)

##### InsightGenerator - 洞察生成器

```python
from src.insights.generator import InsightGenerator
from datetime import datetime

generator = InsightGenerator()

# 生成每日摘要
summary = generator.generate_daily_summary({
    "activities": [
        {"type": "task_completed", "name": "完成报告"},
        {"type": "meeting", "name": "周会"}
    ],
    "date": datetime.now()
})
# 返回: {"type": "daily_summary", "date": "...", "tasks_completed": 1, ...}

# 生成每周回顾
weekly = generator.generate_weekly_review({
    "daily_summaries": [summary1, summary2, ...],
    "week_start": datetime(2026, 3, 17)
})

# 生成里程碑洞察
milestone = generator.generate_milestone_insight({
    "name": "完成 100 个任务",
    "date_achieved": datetime.now(),
    "metrics": {"tasks_completed": 100, "hours_logged": 50}
})
```

##### RecommendationEngine - 推荐引擎

```python
from src.insights.generator import RecommendationEngine

engine = RecommendationEngine()

# 生产力建议
productivity_recs = engine.generate_productivity_recommendations({
    "peak_hours": [9, 10, 14],
    "avg_focus_session": 20,
    "interruption_frequency": "high"
})

# 工作生活平衡建议
balance_recs = engine.generate_work_life_balance_recommendations({
    "avg_daily_hours": 10.5,
    "weekend_work_frequency": 0.7,
    "break_frequency": "low"
})

# 技能发展建议
skill_recs = engine.generate_skill_development_recommendations({
    "skill_gaps": ["Python", "数据分析"],
    "current_skills": ["项目管理"]
})

# 优先级排序
prioritized = engine.prioritize([
    {"text": "建议1", "impact": "high", "effort": "low"},
    {"text": "建议2", "impact": "medium", "effort": "medium"},
])
```

##### ReportGenerator - 报告生成器

```python
from src.insights.generator import ReportGenerator
from datetime import datetime
from pathlib import Path

generator = ReportGenerator()

# 进度报告
progress = generator.generate_progress_report(
    goals=[
        {"name": "阅读书籍", "target": 12, "current": 5, "unit": "本"},
        {"name": "锻炼", "target": 100, "current": 45, "unit": "次"}
    ],
    period_start=datetime(2026, 1, 1),
    period_end=datetime(2026, 3, 31)
)

# 对比报告
comparison = generator.generate_comparison_report(
    period1={"name": "1月", "tasks_completed": 20, "focus_hours": 40},
    period2={"name": "2月", "tasks_completed": 25, "focus_hours": 45}
)

# 导出
output_path = Path("report.json")
generator.export_to_json(progress, output_path)

# Markdown 导出
md_path = Path("report.md")
generator.export_to_markdown({
    "title": "月度报告",
    "sections": [
        {"heading": "完成情况", "content": ["任务 A 完成", "任务 B 进行中"]}
    ]
}, md_path)
```

#### 4. Patterns 模块 (`src.patterns`)

##### BehaviorAnalyzer - 行为分析器

```python
from src.patterns.analyzer import BehaviorAnalyzer
from datetime import datetime

analyzer = BehaviorAnalyzer()

# 检测时间模式
pattern = analyzer.detect_temporal_pattern(
    activities=[
        {"timestamp": datetime(2026, 3, 24, 9, 0), "action": "start_work"},
        {"timestamp": datetime(2026, 3, 25, 9, 15), "action": "start_work"},
        {"timestamp": datetime(2026, 3, 26, 9, 5), "action": "start_work"},
    ],
    action_type="start_work"
)
# 返回: {"detected": True, "type": "daily", "peak_hour": 9, "confidence": 0.9}
```

##### TrendAnalyzer - 趋势分析器

```python
from src.patterns.analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()

# 检测趋势
trend = analyzer.detect_trend([10, 12, 15, 14, 18, 20, 22])
# 返回: {"direction": "increasing", "slope": 1.8, "strength": 0.95, ...}

# 预测
forecasts = analyzer.forecast([10, 12, 15, 14, 18], periods=3)
# 返回: [20.5, 22.1, 23.7]
```

##### AnomalyDetector - 异常检测器

```python
from src.patterns.analyzer import AnomalyDetector

 detector = AnomalyDetector()

# 检测异常值
outliers = detector.detect_outliers([10, 12, 11, 13, 100, 12, 11])
# 返回: [{"index": 4, "value": 100, "z_score": 3.2, ...}]

# 检测模式中断
breaks = detector.detect_pattern_breaks(activities)

# 计算异常分数
score = detector.calculate_anomaly_score(50, baseline=[10, 12, 11, 13, 12])
# 返回: 0.0-1.0 的分数
```

##### ProductivityAnalyzer - 生产力分析器

```python
from src.patterns.analyzer import ProductivityAnalyzer

analyzer = ProductivityAnalyzer()

# 找出高效时段
peak_hours = analyzer.find_peak_productivity_hours([
    {"start": datetime(2026, 3, 24, 9, 0), "output": 10},
    {"start": datetime(2026, 3, 24, 14, 0), "output": 8},
    {"start": datetime(2026, 3, 24, 21, 0), "output": 3},
])
# 返回: {9: 10.0, 14: 8.0, 21: 3.0}

# 分析完成模式
patterns = analyzer.analyze_completion_patterns([
    {"type": "coding", "created": datetime(...), "completed": datetime(...)},
    {"type": "meeting", "created": datetime(...), "completed": datetime(...)},
])

# 识别干扰模式
distractions = analyzer.identify_distraction_patterns(activities)
```

#### 5. Security 模块 (`src.security`)

##### Vault - 密钥管理

```python
from src.security.vault import Vault

vault = Vault()

# 存储密钥
vault.store_key("api_key", "secret_value", key_type="api")

# 获取密钥
value = vault.get_key("api_key")

# 删除密钥
vault.delete_key("api_key")
```

##### Encryption - 加密工具

```python
from src.security.encryption import Encryption

crypto = Encryption()

# 加密/解密
ciphertext = crypto.encrypt("敏感数据", key="password")
plaintext = crypto.decrypt(ciphertext, key="password")
```

**实际使用场景 - 加密日志内容**:
```python
from src.journal.core import JournalEntry, JournalManager
from src.security.encryption import Encryption
import sqlite3

# 加密敏感日志
conn = sqlite3.connect("opc200.db")
manager = JournalManager(conn)
crypto = Encryption()

# 加密后存储
sensitive_content = "客户联系方式: 138-xxxx-xxxx"
encrypted = crypto.encrypt(sensitive_content, key="user_password")

entry = JournalEntry(
    content=encrypted,  # 存储加密内容
    tags=["加密", "敏感"],
    metadata={"encrypted": True}
)
manager.create_entry(entry)

# 读取时解密
entry = manager.get_entry(entry_id)
if entry.get_metadata("encrypted"):
    plaintext = crypto.decrypt(entry.content, key="user_password")
```

**实际使用场景 - API 密钥管理**:
```python
from src.security.vault import Vault

vault = Vault()

# 存储外部服务 API 密钥
vault.store_key("openai_api_key", "sk-...", key_type="api")
vault.store_key("qdrant_token", "...", key_type="token")

# 在代码中使用
def call_openai():
    api_key = vault.get_key("openai_api_key")
    # 使用 api_key 调用服务...
```

---

## 性能与限制

### 性能基准

| 操作 | 典型耗时 | 限制说明 |
|------|----------|----------|
| JournalEntry 创建 | < 10ms | 无限制 |
| 日志查询 (list_entries) | < 50ms (1000条) | 默认 limit=100, max=10000 |
| 标签搜索 | < 100ms | 全表扫描，大数据量建议加索引 |
| 语义搜索 (VectorStore) | 500ms-2s | 首次加载模型 ~5s |
| 加密操作 | < 5ms | 与内容长度成正比 |
| 任务调度 (Cron) | < 1ms | 无限制 |

### 存储限制

| 项目 | 限制 | 建议 |
|------|------|------|
| 日志内容长度 | 无硬限制 | 建议 < 10MB，大文本考虑分片 |
| 标签数量/条目 | 无硬限制 | 建议 < 50，过多影响查询性能 |
| 元数据大小 | 无硬限制 | 建议 < 100KB，JSON 序列化存储 |
| 向量存储条目 | 内存限制 | 大规模请使用 Qdrant 后端 |
| SQLite 数据库 | 无硬限制 | 建议 10GB 以下，定期归档 |

### 并发安全

- **JournalManager**: 线程安全（SQLite WAL 模式）
- **Vault**: 非线程安全，建议单例模式使用
- **TaskScheduler**: 非线程安全，单线程使用
- **VectorStore**: 非线程安全，查询和写入分开处理

### 最佳实践

1. **批量操作**: 大量条目使用事务批量插入
   ```python
   with conn:
       for entry in entries:
           manager.create_entry(entry)
   ```

2. **定期归档**: 超过 1 年的日志归档到历史表

3. **索引优化**: 高频查询字段添加索引
   ```sql
   CREATE INDEX idx_entries_created ON entries(created_at);
   CREATE INDEX idx_entries_tags ON entries(tags);
   ```

---

## RESTful API（规划中）

> **注意**: 以下 API 为规划设计，尚未实现 HTTP 服务端。

### Base URL

```
http://localhost:8080/api/v1
```

### 认证

Bearer Token:
```
Authorization: Bearer {token}
```

### 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 token 无效 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

### 端点详情

#### 日志条目管理

##### 列出租用
```http
GET /journal/entries?limit=20&offset=0&tag=工作
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "total": 150,
  "offset": 0,
  "limit": 20,
  "entries": [
    {
      "id": "je-550e8400-e29b-41d4-a716-446655440000",
      "content": "完成了 API 文档编写",
      "tags": ["工作", "开发"],
      "metadata": {"project": "OPC200"},
      "created_at": "2026-04-01T10:30:00Z",
      "updated_at": "2026-04-01T10:30:00Z"
    }
  ]
}
```

##### 创建条目
```http
POST /journal/entries
Content-Type: application/json
Authorization: Bearer {token}

{
  "content": "今天完成了产品原型的设计",
  "tags": ["产品设计", "里程碑"],
  "metadata": {
    "mood": "productive",
    "energy_level": 8
  }
}
```

**响应 201**:
```json
{
  "id": "je-550e8400-e29b-41d4-a716-446655440001",
  "content": "今天完成了产品原型的设计",
  "tags": ["产品设计", "里程碑"],
  "metadata": {
    "mood": "productive",
    "energy_level": 8
  },
  "created_at": "2026-04-01T14:30:00Z",
  "updated_at": "2026-04-01T14:30:00Z"
}
```

**响应 400**:
```json
{
  "error": "ValidationError",
  "message": "content 字段不能为空"
}
```

##### 获取条目
```http
GET /journal/entries/{id}
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "id": "je-550e8400-e29b-41d4-a716-446655440000",
  "content": "完成了 API 文档编写",
  "tags": ["工作", "开发"],
  "metadata": {"project": "OPC200"},
  "created_at": "2026-04-01T10:30:00Z",
  "updated_at": "2026-04-01T10:30:00Z"
}
```

**响应 404**:
```json
{
  "error": "NotFoundError",
  "message": "条目不存在"
}
```

##### 更新条目
```http
PUT /journal/entries/{id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "content": "完成了 API 文档编写（已修订）",
  "tags": ["工作", "开发", "文档"]
}
```

**响应 200**: 返回更新后的条目

##### 删除条目
```http
DELETE /journal/entries/{id}
Authorization: Bearer {token}
```

**响应 204**: 无内容（删除成功）

##### 搜索内容
```http
GET /journal/search?q=关键词&limit=10
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "query": "关键词",
  "total": 25,
  "results": [
    {
      "entry": {
        "id": "je-550e8400-e29b-41d4-a716-446655440000",
        "content": "包含关键词的日志内容...",
        "tags": ["工作"],
        "metadata": {},
        "created_at": "2026-04-01T10:30:00Z"
      },
      "score": 0.95
    }
  ]
}
```

#### 任务管理

##### 列出租务
```http
GET /tasks?status=pending
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "tasks": [
    {
      "id": "task-001",
      "type": "recurring",
      "description": "每日备份",
      "status": "pending",
      "created_at": "2026-04-01T00:00:00Z",
      "deadline": "2026-04-01T23:59:59Z"
    }
  ]
}
```

##### 创建任务
```http
POST /tasks
Content-Type: application/json
Authorization: Bearer {token}

{
  "type": "one_time",
  "description": "整理文档",
  "deadline": "2026-04-02T18:00:00Z"
}
```

**响应 201**: 返回创建的任务

#### 洞察生成

##### 每日摘要
```http
GET /insights/daily?date=2026-04-01
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "type": "daily_summary",
  "date": "2026-04-01",
  "tasks_completed": 5,
  "meetings": 2,
  "total_activities": 7,
  "summary": "今日完成了 5 个任务，参加了 2 个会议，整体效率较高"
}
```

##### 每周回顾
```http
GET /insights/weekly?week_start=2026-03-24
Authorization: Bearer {token}
```

**响应 200**:
```json
{
  "type": "weekly_review",
  "week_start": "2026-03-24",
  "week_end": "2026-03-30",
  "total_tasks": 25,
  "completed_tasks": 22,
  "productivity_trend": "increasing",
  "highlights": ["完成了项目里程碑", "学习了新技术"]
}
```

### 端点概览表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/journal/entries` | GET | 列出租用 |
| `/journal/entries` | POST | 创建条目 |
| `/journal/entries/{id}` | GET | 获取条目 |
| `/journal/entries/{id}` | PUT | 更新条目 |
| `/journal/entries/{id}` | DELETE | 删除条目 |
| `/journal/search` | GET | 搜索内容 |
| `/tasks` | GET | 列出租务 |
| `/tasks` | POST | 创建任务 |
| `/insights/daily` | GET | 每日摘要 |
| `/insights/weekly` | GET | 每周回顾 |

---

## 数据模型

### JournalEntry

```python
{
    "id": "uuid",
    "content": "str",           # 必填
    "tags": ["str"],            # 默认: []
    "metadata": {"key": "value"},  # 默认: {}
    "created_at": "datetime",   # ISO 8601
    "updated_at": "datetime"
}
```

### Task

```python
{
    "id": "str",
    "type": "str",
    "description": "str",
    "status": "pending|processing|completed|failed",
    "created_at": "datetime",
    "deadline": "datetime?",
    "result": "any?"
}
```

### DailySummary

```python
{
    "type": "daily_summary",
    "date": "YYYY-MM-DD",
    "tasks_completed": int,
    "meetings": int,
    "total_activities": int,
    "summary": "str"
}
```

---

## 错误处理

### 异常类型

```python
from src.exceptions import (
    OPC200Error,           # 基础异常
    ValidationError,       # 验证错误
    StorageError,          # 存储错误
    SecurityError,         # 安全错误
    NotFoundError,         # 资源不存在
    AuthenticationError,   # 认证失败
)
```

### 使用示例

```python
from src.utils.validation import InputValidator, ValidationError

try:
    validated = InputValidator.validate_entry_id(entry_id)
except ValidationError as e:
    print(f"验证失败: {e}")
```

---

## 完整示例

### 工作流示例

```python
import sqlite3
from datetime import datetime
from src.journal.core import JournalManager, JournalEntry
from src.insights.generator import InsightGenerator

# 初始化
conn = sqlite3.connect("opc200.db")
manager = JournalManager(conn)
manager.create_table()

# 记录工作日志
entry = JournalEntry(
    content="完成了 OPC200 API 文档的编写",
    tags=["开发", "文档", "API"],
    metadata={
        "project": "OPC200",
        "mood": "productive",
        "energy": 8
    }
)
manager.create_entry(entry)

# 记录多个活动
activities = []
for i in range(5):
    e = JournalEntry(
        content=f"任务 {i+1}",
        tags=["任务"],
        metadata={"completed": True}
    )
    manager.create_entry(e)
    activities.append({"type": "task_completed", "name": f"任务 {i+1}"})

# 生成每日摘要
generator = InsightGenerator()
summary = generator.generate_daily_summary({
    "activities": activities,
    "date": datetime.now()
})

print(f"今日完成: {summary['tasks_completed']} 个任务")
print(f"总结: {summary['summary']}")
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.3.0 | 2026-04-01 | 优化 API 文档：统一版本号、补充 VectorStore 依赖说明、添加性能与限制章节、完善 RESTful API 示例 |
| v2.2.2 | 2026-04-01 | 完善 Python API 文档，补充完整示例 |
| v2.2.0 | 2026-03-30 | 初始版本 |

---

## 相关文档

- [README.md](../README.md) - 项目概览
- [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) - 开发计划
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) - 项目状态
