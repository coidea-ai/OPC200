# OPC200 API 文档

## 概述

OPC200 提供 RESTful API 用于与核心功能交互。

**Base URL**: `http://localhost:8080/api/v1`

**认证**: Bearer Token

## 端点

### Journal API

#### 创建日志条目

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

**响应**:
```json
{
  "id": "JE-20260324-001",
  "content": "今天完成了产品原型的设计",
  "tags": ["产品设计", "里程碑"],
  "metadata": {
    "mood": "productive",
    "energy_level": 8
  },
  "created_at": "2026-03-24T10:30:00Z",
  "updated_at": "2026-03-24T10:30:00Z"
}
```

#### 获取日志条目

```http
GET /journal/entries/{entry_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "id": "JE-20260324-001",
  "content": "今天完成了产品原型的设计",
  "tags": ["产品设计", "里程碑"],
  "metadata": {...},
  "created_at": "2026-03-24T10:30:00Z",
  "updated_at": "2026-03-24T10:30:00Z"
}
```

#### 列出日志条目

```http
GET /journal/entries?limit=10&offset=0&tag=里程碑
Authorization: Bearer {token}
```

**响应**:
```json
{
  "items": [...],
  "total": 100,
  "limit": 10,
  "offset": 0
}
```

#### 搜索日志

```http
GET /journal/search?q=产品原型&limit=5
Authorization: Bearer {token}
```

### Vector Store API

#### 语义搜索

```http
POST /vectors/search
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "如何提高工作效率",
  "limit": 10,
  "tags": ["效率", "时间管理"]
}
```

#### 查找相似条目

```http
GET /vectors/similar/{entry_id}?limit=5
Authorization: Bearer {token}
```

### Tasks API

#### 创建异步任务

```http
POST /tasks
Content-Type: application/json
Authorization: Bearer {token}

{
  "type": "research",
  "description": "竞品分析报告",
  "deadline": "2026-03-25T08:00:00Z"
}
```

#### 获取任务状态

```http
GET /tasks/{task_id}
Authorization: Bearer {token}
```

### Insights API

#### 获取每日摘要

```http
GET /insights/daily?date=2026-03-24
Authorization: Bearer {token}
```

#### 获取每周回顾

```http
GET /insights/weekly?week_start=2026-03-17
Authorization: Bearer {token}
```

#### 获取建议

```http
POST /insights/recommendations
Content-Type: application/json
Authorization: Bearer {token}

{
  "type": "productivity",
  "context": {
    "current_workload": "high",
    "upcoming_deadlines": ["产品发布"]
  }
}
```

## 数据模型

### JournalEntry

```typescript
interface JournalEntry {
  id: string;
  content: string;
  tags: string[];
  metadata: Record<string, any>;
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
}
```

### Task

```typescript
interface Task {
  id: string;
  type: string;
  description: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  deadline?: string;
  result?: any;
}
```

## 错误码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未授权，token 无效 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 429 | Too Many Requests | 请求频率超限 |
| 500 | Internal Server Error | 服务器内部错误 |

## 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Content cannot be empty",
    "details": {
      "field": "content",
      "constraint": "required"
    }
  }
}
```

## 限流

- 默认: 60 请求/分钟
- 搜索: 30 请求/分钟
- 批量操作: 10 请求/分钟

## SDK

### Python

```python
from opc200 import Client

client = Client("http://localhost:8080", token="your-token")

# 创建日志条目
entry = client.journal.create(
    content="今天完成了产品原型的设计",
    tags=["产品设计"]
)

# 搜索
results = client.journal.search("产品原型")
```

### JavaScript

```javascript
import { OPC200Client } from '@coidea/opc200-sdk';

const client = new OPC200Client('http://localhost:8080', {
  token: 'your-token'
});

// 创建日志条目
const entry = await client.journal.create({
  content: '今天完成了产品原型的设计',
  tags: ['产品设计']
});

// 搜索
const results = await client.journal.search('产品原型');
```
