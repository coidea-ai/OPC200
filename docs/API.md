# OPC200 API 文档

> 版本: 2026.1  
> Base URL: `https://api.opc200.co/v1` 或 Gateway 本地地址

---

## 认证

所有 API 请求需要包含认证 Token:

```http
Authorization: Bearer {token}
```

---

## 核心 API

### Gateway 状态

```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "2026.3.12",
  "uptime": 86400,
  "timestamp": "2026-03-24T10:00:00Z"
}
```

---

### Journal 管理

#### 获取今日 Journal

```http
GET /journal/today
```

**响应**:
```json
{
  "date": "2026-03-24",
  "entries": [
    {
      "id": "entry-001",
      "time": "09:00:00",
      "type": "task",
      "content": "完成产品需求文档",
      "metadata": {
        "status": "completed",
        "duration_minutes": 120
      }
    }
  ],
  "summary": {
    "tasks_completed": 5,
    "tasks_pending": 2,
    "insights": ["上午效率最高"]
  }
}
```

#### 创建 Journal 条目

```http
POST /journal/entries
Content-Type: application/json

{
  "type": "note",
  "content": "重要想法记录",
  "tags": ["idea", "product"],
  "metadata": {
    "priority": "high"
  }
}
```

---

### 任务管理

#### 创建异步任务

```http
POST /tasks
Content-Type: application/json

{
  "title": "竞品分析",
  "description": "分析竞争对手 X 的定价策略",
  "agent": "research",
  "priority": "normal",
  "due_time": "2026-03-25T09:00:00Z"
}
```

**响应**:
```json
{
  "task_id": "TASK-20260324-001",
  "status": "queued",
  "estimated_duration": "30m",
  "created_at": "2026-03-24T10:00:00Z"
}
```

#### 获取任务状态

```http
GET /tasks/{task_id}
```

**响应**:
```json
{
  "task_id": "TASK-20260324-001",
  "status": "completed",
  "progress": 100,
  "result": {
    "summary": "分析完成",
    "details_url": "/tasks/TASK-20260324-001/result"
  },
  "completed_at": "2026-03-24T10:25:00Z"
}
```

---

### Agent 管理

#### 列出可用 Agents

```http
GET /agents
```

**响应**:
```json
{
  "agents": [
    {
      "id": "primary",
      "name": "主 Agent",
      "status": "active",
      "capabilities": ["conversation", "task_management"]
    },
    {
      "id": "research",
      "name": "Research Agent",
      "status": "idle",
      "capabilities": ["web_search", "data_analysis"]
    }
  ]
}
```

#### 切换 Agent

```http
POST /session/agent
Content-Type: application/json

{
  "agent_id": "research"
}
```

---

### 记忆管理

#### 搜索记忆

```http
POST /memory/search
Content-Type: application/json

{
  "query": "上周的营销策略",
  "type": "all",
  "limit": 10
}
```

**响应**:
```json
{
  "results": [
    {
      "id": "mem-001",
      "type": "structured",
      "content": "讨论了内容营销 vs 付费广告",
      "relevance": 0.95,
      "created_at": "2026-03-18T14:00:00Z"
    }
  ],
  "total": 5
}
```

#### 存储事实

```http
POST /memory/facts
Content-Type: application/json

{
  "key": "user_preferred_working_hours",
  "value": {
    "start": "09:00",
    "end": "18:00",
    "timezone": "Asia/Shanghai"
  },
  "ttl_days": 365
}
```

---

### 模式识别

#### 获取工作模式

```http
GET /patterns/work-style
```

**响应**:
```json
{
  "patterns": {
    "productive_hours": ["09:00-11:00", "14:00-16:00"],
    "work_style": "deep_focus",
    "stress_signals": ["连续会议 > 3h"],
    "preferences": {
      "break_interval": 120,
      "communication_style": "direct"
    }
  },
  "confidence": 0.87,
  "based_on_days": 30
}
```

---

### 里程碑

#### 列出里程碑

```http
GET /milestones
```

**响应**:
```json
{
  "milestones": [
    {
      "id": "ms-001",
      "name": "首周成就",
      "description": "连续使用 7 天",
      "achieved_at": "2026-03-07T00:00:00Z",
      "badge": "🥉"
    },
    {
      "id": "ms-002",
      "name": "百日指挥官",
      "description": "连续使用 100 天",
      "achieved_at": null,
      "progress": 75,
      "badge": "💎"
    }
  ]
}
```

---

### 洞察生成

#### 获取周洞察

```http
GET /insights/weekly
```

**响应**:
```json
{
  "period": "2026-03-17 to 2026-03-24",
  "summary": "本周工作效率提升 15%",
  "highlights": [
    "完成了 3 个重要项目",
    "深度工作时间增加"
  ],
  "recommendations": [
    "继续保持上午深度工作习惯",
    "考虑减少下午会议数量"
  ],
  "metrics": {
    "tasks_completed": 25,
    "deep_work_hours": 18,
    "avg_response_time_minutes": 5
  }
}
```

---

## WebSocket API

### 实时会话

```javascript
const ws = new WebSocket('wss://opc-xxx.opc200.co/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

// 发送消息
ws.send(JSON.stringify({
  type: 'message',
  content: '帮我分析今天的任务',
  context: {
    agent: 'primary'
  }
}));
```

---

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "认证令牌无效或已过期",
    "details": {
      "token_expired_at": "2026-03-24T00:00:00Z"
    }
  }
}
```

### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| `INVALID_TOKEN` | 401 | 认证令牌无效 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 限流

- 默认: 60 请求/分钟
- 批量操作: 10 请求/分钟
- WebSocket: 100 消息/分钟

---

## SDK

### JavaScript/TypeScript

```bash
npm install @opc200/sdk
```

```typescript
import { OPC200Client } from '@opc200/sdk';

const client = new OPC200Client({
  gatewayUrl: 'https://opc-xxx.opc200.co',
  token: 'your-token'
});

// 获取今日 Journal
const journal = await client.journal.getToday();

// 创建任务
const task = await client.tasks.create({
  title: '竞品分析',
  agent: 'research'
});

// 监听实时消息
client.onMessage((message) => {
  console.log(message);
});
```

### Python

```bash
pip install opc200
```

```python
from opc200 import Client

client = Client(
    gateway_url='https://opc-xxx.opc200.co',
    token='your-token'
)

# 获取今日 Journal
journal = client.journal.get_today()

# 创建任务
task = client.tasks.create(
    title='竞品分析',
    agent='research'
)
```

---

## 变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 2026.1 | 2026-03-24 | 初始版本 |

---

*详细实现请参考 [GitHub](https://github.com/coidea/opc200)*
