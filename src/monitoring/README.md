# OPC200 监控埋点指南

本文档介绍如何在 OPC200 核心模块中添加 Prometheus 指标埋点。

## 概述

OPC200 使用 Prometheus 格式暴露指标，通过 `metrics-server` 服务提供 `/metrics` 端点供 Prometheus 抓取。

### 指标类型

| 类型 | 用途 | 示例 |
|------|------|------|
| Counter | 累计计数（只增不减） | 请求次数、错误次数 |
| Histogram | 分布统计（耗时、大小） | 响应时间、数据大小 |
| Gauge | 瞬时值（可增可减） | 队列长度、成功率 |

## 快速开始

### 1. 继承 MetricsMixin

```python
from src.monitoring.instrumentation import MetricsMixin

class MyClass(MetricsMixin):
    def __init__(self):
        super().__init__()
        self._init_metrics("my_class")  # 指标前缀
```

### 2. 使用装饰器埋点

```python
class MyClass(MetricsMixin):
    
    @MetricsMixin.counted("operations_total", operation="create")
    @MetricsMixin.timed("operation_duration_seconds", operation="create")
    def create_something(self):
        # 业务逻辑
        pass
```

### 3. 手动记录指标

```python
class MyClass(MetricsMixin):
    
    def do_something(self):
        # 记录计数器
        self._record_counter("events_total", event_type="user_action")
        
        # 记录耗时
        self._record_histogram("process_duration_seconds", 0.5)
        
        # 记录瞬时值
        self._record_gauge("queue_size", len(self.queue))
```

## 核心模块指标

### JournalManager

指标前缀: `journal_manager_`

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `entries_total` | Counter | operation | 条目操作次数 (create/get/list/search) |
| `operation_duration_seconds` | Histogram | operation | 操作耗时 |

示例:
```
journal_manager_entries_total{operation="create"} 42
journal_manager_operation_duration_seconds{operation="search"} 0.015
```

### TaskScheduler

指标前缀: `task_scheduler_`

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `jobs_total` | Counter | operation | 任务操作次数 (add/remove) |

### RecurringTask

指标前缀: `recurring_task_`

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `executions_total` | Counter | operation, status | 执行次数 (success/failure) |
| `success_rate` | Gauge | task_id | 成功率 |

示例:
```
recurring_task_executions_total{operation="execute",status="success"} 100
recurring_task_success_rate{task_id="daily_backup"} 0.98
```

### InsightGenerator

指标前缀: `insight_generator_`

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `insights_total` | Counter | type | 生成洞察次数 |
| `generation_duration_seconds` | Histogram | type | 生成耗时 |

示例:
```
insight_generator_insights_total{type="daily_summary"} 30
insight_generator_generation_duration_seconds{type="weekly_review"} 0.25
```

## 添加新指标的最佳实践

### 1. 命名规范

- 使用小写字母和下划线分隔
- 以单位结尾：`_seconds`, `_bytes`, `_total`
- 示例: `http_request_duration_seconds`, `entries_created_total`

### 2. 标签设计

- 使用有意义的标签名
- 避免标签值过多（会导致高基数）
- 示例标签: `operation`, `status`, `endpoint`

### 3. 性能考虑

- 装饰器有极小性能开销，生产环境可接受
- 对于极高频操作（>1000次/秒），考虑采样
- 避免在循环中创建动态标签

### 4. 测试验证

```python
def test_metrics_recorded():
    collector = MetricsCollector()
    manager = JournalManager(conn, collector=collector)
    
    manager.create_entry(entry)
    
    # 验证指标
    samples = collector.get_samples("journal_manager_entries_total")
    assert len(samples) > 0
```

## 本地验证

启动 metrics-server 并检查指标:

```bash
# 启动服务
python src/api/metrics_server.py --port 9091 --with-app-metrics

# 查看指标
curl http://localhost:9091/metrics

# 查看健康状态
curl http://localhost:9091/health
```

## Prometheus 配置

Prometheus 自动从 `metrics-server:9091` 抓取指标:

```yaml
scrape_configs:
  - job_name: 'opc200-metrics'
    static_configs:
      - targets: ['metrics-server:9091']
    metrics_path: /metrics
    scrape_interval: 15s
```

## 故障排查

### 指标未显示

1. 检查 `_init_metrics()` 是否被调用
2. 确认装饰器顺序：`@counted` 应在 `@timed` 之上
3. 验证 metrics-server 是否运行

### 标签值错误

- 标签值必须是字符串
- 避免使用可变对象作为标签值

### 性能问题

- 使用 Prometheus 的 `rate()` 函数计算 QPS
- 高基数标签会导致内存问题
