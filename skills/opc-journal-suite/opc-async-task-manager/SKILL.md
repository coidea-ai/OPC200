# opc-async-task-manager

## Description

OPC Journal Suite Async Task Management Module - Supports 7×24 background task execution, allowing users to "delegate and rest assured", receiving results the next morning.

## When to use

- User says "run in background", "give me results tomorrow morning", "I'm going to sleep, keep processing"
- Long-running research tasks
- Tasks waiting for external APIs
- Non-urgent but important background processing

## Core Concepts

### Task Lifecycle

```
Created → Queued → Assigned → Running → Complete/Failed → Notified
   │          │          │          │            │           │
   │          │          │          │            │           └── Notify user
   │          │          │          │            └── Result processing
   │          │          │          └── Running (monitorable)
   │          │          └── Assigned to Agent
   │          └── Waiting for resources
   └── User creates task
```

### Task Types

| 类型 | 执行时间 | 示例 | 优先级 |
|------|---------|------|--------|
| Quick | < 5 min | 简单查询、格式转换 | High |
| Standard | 5-60 min | 文档生成、数据分析 | Medium |
| Long | 1-8 hours | 深度研究、批量处理 | Low |
| Overnight | 8+ hours | 整夜运行、复杂计算 | Lowest |

## Usage

### Create Async Task

User: "我需要一份竞品分析报告，明天早上 8 点要"

System:
```python
task = async_manager.create(
    customer_id="OPC-001",
    title="竞品分析报告",
    description="分析 5 个主要竞争对手的产品功能、定价策略",
    
    # 执行配置
    task_type="research",
    estimated_duration="4h",
    agent="ResearchAgent",
    
    # 时间约束
    deadline="tomorrow 08:00",
    earliest_start="now",
    
    # 通知设置
    notify_on_complete=True,
    notify_channels=["feishu"],
    
    # 输出格式
    output_format="markdown_report",
    output_location="customers/OPC-001/reports/competitor-analysis-20260321.md",
    
    # 依赖
    dependencies=[],
    
    # 回调
    on_complete="generate_digest_and_notify",
    on_fail="escalate_to_support"
)

# Returns: TASK-20260321-007
```

Bot Response:
```
✅ 异步任务已创建

任务编号: #RESEARCH-007
任务类型: 竞品研究
分配给: Research Agent
预计耗时: 4 小时
截止时间: 明天 08:00

执行计划:
• 22:00 - 开始数据收集
• 00:00 - 竞品功能对比  
• 02:00 - 定价策略分析
• 06:00 - 报告生成
• 08:00 - 通知您完成

完成后将:
1. 发送飞书通知
2. 生成执行摘要
3. 更新您的 Journal
4. 如有重要发现，标记为待阅读

晚安！💤
```

### Monitor Task

User: "RESEARCH-007 进展如何？"

System:
```python
status = async_manager.status("RESEARCH-007")
```

Response:
```
📊 任务 #RESEARCH-007 状态

状态: 执行中 (62%)
开始时间: 22:00
已用时: 2.5 小时
预计完成: 02:30 (提前！)

当前阶段: 定价策略分析
   ████████████████░░░░ 62%

最近日志:
[00:15] 完成 3/5 竞品功能对比
[00:45] 发现竞品 A 的新功能，已记录
[01:20] 开始定价分析

Agent 状态: 正常运行
暂无阻塞

是否需要:
• 查看详细日志
• 暂停/取消任务
• 修改截止时间
```

### Task Results

```
☀️ 早上好！任务 #RESEARCH-007 已完成

⏱️ 执行统计
计划时间: 8 小时
实际用时: 6.5 小时 (提前 1.5h!)

📄 交付物
位置: /reports/competitor-analysis-20260321.md
格式: Markdown (12 页)

🔍 关键发现 (AI 生成的摘要)
1. 竞品 A 上周发布了您规划中的功能
   → 建议加速您的开发节奏
   
2. 市场平均定价低于您的预期 20%
   → 建议重新评估定价策略
   
3. 竞品 B 的客户支持评分较低
   → 这是您的差异化机会

📌 后续建议
已自动创建任务:
• #STRATEGY-008: 重新评估定价 (建议今天处理)
• #DEV-009: 加速功能开发 (优先级: High)

💾 已同步
• Journal 条目: JE-20260322-001
• 知识库: competitors/2026-03-update

[查看完整报告] [标记为已读] [创建后续任务]
```

## Agent Pool Management

```python
# Agent 资源池
agent_pool = {
    "ResearchAgent": {
        "capacity": 5,      # 并发数
        "current_load": 3,
        "queue_length": 2,
        "avg_task_time": "2h"
    },
    "DevAgent": {
        "capacity": 3,
        "current_load": 1,
        "queue_length": 0,
        "avg_task_time": "4h"
    },
    "WritingAgent": {
        "capacity": 2,
        "current_load": 2,
        "queue_length": 5,  # 繁忙
        "avg_task_time": "1h"
    }
}

# 智能调度
def schedule_task(task):
    # 选择负载最低的合适 Agent
    available_agents = filter(
        lambda a: a.type == task.required_type and a.queue_length < 3,
        agent_pool
    )
    
    return min(available_agents, key=lambda a: a.estimated_wait_time)
```

## Error Handling & Recovery

```python
# 失败处理策略
error_handlers = {
    "api_timeout": {
        "action": "retry",
        "max_retries": 3,
        "backoff": "exponential"
    },
    "rate_limit": {
        "action": "retry",
        "delay": "1h"
    },
    "agent_crash": {
        "action": "reassign",
        "to": "backup_agent"
    },
    "deadline_approaching": {
        "action": "escalate",
        "notify": ["user", "support"]
    }
}

# 用户侧错误处理
when task_failed:
    if recoverable:
        # 自动重试
        retry_task(task)
        notify_user(f"任务遇到临时问题，正在自动重试...")
    else:
        # 需要人工介入
        notify_user(f"""
        ⚠️ 任务 #{task.id} 需要您的关注
        
        问题: {task.error_message}
        已尝试: {task.retry_count} 次
        
        选项:
        • [重试任务]
        • [修改参数后重试]
        • [转人工处理]
        • [取消任务]
        """)
```

## Overnight Queue

```python
# 夜间任务队列（用户睡眠时执行）
overnight_queue = {
    "window": "22:00 - 08:00",
    "max_concurrent": 10,
    "priority_rules": [
        # 用户明确 deadline 的任务优先
        lambda t: t.has_explicit_deadline,
        # 长时间任务优先（充分利用夜间）
        lambda t: t.estimated_duration > "4h",
        # 创建时间早的任务优先
        lambda t: t.created_at
    ]
}

# 智能排序
def prioritize_overnight_tasks(tasks):
    return sorted(tasks, key=lambda t: (
        not t.has_explicit_deadline,  # deadline 优先
        -t.estimated_duration,          # 长时间优先
        t.created_at                    # 先创建的先执行
    ))
```

## Configuration

```yaml
async_task_manager:
  # 资源限制
  max_concurrent_per_customer: 5
  max_queue_depth: 20
  
  # 执行策略
  scheduling:
    algorithm: "fair_share"  # fair_share / priority / fifo
    preemption: false        # 是否允许抢占
    
  # 重试策略
  retry:
    max_attempts: 3
    backoff_strategy: "exponential"  # fixed / linear / exponential
    
  # 监控
  monitoring:
    heartbeat_interval: "5m"
    progress_update: "25%"  # 每 25% 更新一次
    
  # 通知
  notification:
    on_start: false
    on_progress: false
    on_complete: true
    on_fail: true
    channels: ["feishu"]
    
  # 超时处理
  timeout:
    default: "8h"
    max: "24h"
    action_on_timeout: "notify_and_escalate"
```

## Best Practices

1. **明确期望** - 清晰的 deadline 和输出格式
2. **适度委托** - 不是一切都适合异步，保留即时互动
3. **及时跟进** - 早上第一件事检查 overnight 任务结果
4. **错误反馈** - 失败时提供清晰的下一步选项
5. **资源公平** - 确保所有客户的任务都能被及时处理
