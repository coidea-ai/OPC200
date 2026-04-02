# OPC200 监控运维手册

> 版本: v2.3.0  
> 更新日期: 2026-04-02

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     OPC200 监控架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐         ┌──────────────┐                 │
│   │   Grafana    │◄────────│  Prometheus  │                 │
│   │   :3000      │         │   :9090      │                 │
│   └──────────────┘         └──────┬───────┘                 │
│          ▲                        │                         │
│          │                        │ scrape                  │
│          │                 ┌──────▼───────┐                 │
│          │                 │ Metrics      │                 │
│          │                 │ Server       │                 │
│          │                 │ :9091        │                 │
│          │                 └──────┬───────┘                 │
│          │                        │                         │
│          │           ┌────────────┼────────────┐           │
│          │           ▼            ▼            ▼           │
│          │    ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│          │    │ Journal │  │ Tasks   │  │ Insight │       │
│          │    │ Manager │  │ Scheduler│  │ Generator│      │
│          │    └─────────┘  └─────────┘  └─────────┘       │
│          │                                                 │
│   ┌──────┴──────────────────────────────────────────┐     │
│   │              Grafana Dashboards                  │     │
│   │  • OPC200 Overview (概览)                        │     │
│   │  • OPC200 详细监控                               │     │
│   └──────────────────────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 启动监控栈

```bash
# 启动所有监控相关服务
docker-compose up -d prometheus grafana metrics-server

# 验证服务状态
docker-compose ps prometheus grafana metrics-server

# 查看日志
docker-compose logs -f metrics-server
```

### 访问界面

| 服务 | URL | 默认凭证 |
|------|-----|----------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Metrics Server | http://localhost:9091/metrics | - |

---

## 指标说明

### Journal 模块指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `journal_manager_entries_total` | Counter | 条目操作次数，标签: operation=(create\|get\|list\|search\|update\|delete) |
| `journal_manager_operation_duration_seconds` | Histogram | 操作耗时，标签: operation=... |

**常用查询**:
```promql
# Journal QPS
sum(rate(journal_manager_entries_total[5m])) by (operation)

# P95 搜索耗时
histogram_quantile(0.95, 
  sum(rate(journal_manager_operation_duration_seconds_bucket{operation="search"}[5m])) by (le)
)
```

### Task 模块指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `task_scheduler_jobs_total` | Counter | 任务操作次数 |
| `recurring_task_executions_total` | Counter | 任务执行次数，标签: status=(success\|failure) |
| `recurring_task_success_rate` | Gauge | 任务成功率 |

**常用查询**:
```promql
# 任务执行率
sum(rate(recurring_task_executions_total[5m])) by (status)

# 任务成功率
avg(recurring_task_success_rate) by (task_id)
```

### Insight 模块指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `insight_generator_insights_total` | Counter | 生成洞察次数，标签: type=(daily_summary\|weekly_review\|milestone) |
| `insight_generator_generation_duration_seconds` | Histogram | 生成耗时 |

---

## 告警规则

### 服务可用性告警

| 告警名 | 级别 | 条件 | 处理建议 |
|--------|------|------|----------|
| OPC200MetricsServerDown | Critical | up==0 持续1分钟 | 检查 metrics-server 容器状态 |
| OPC200GatewayDown | Warning | up==0 持续2分钟 | 检查 gateway 服务 |

### 资源使用告警

| 告警名 | 级别 | 条件 | 处理建议 |
|--------|------|------|----------|
| HighDiskUsage | Warning | 磁盘使用率 > 80% | 清理日志或扩容 |
| CriticalDiskUsage | Critical | 磁盘使用率 > 90% | 立即处理，可能宕机 |
| HighMemoryUsage | Warning | 内存使用率 > 90% | 重启服务或扩容 |
| CriticalMemoryUsage | Critical | 内存使用率 > 95% | 立即处理，可能OOM |

### 性能告警

| 告警名 | 级别 | 条件 | 处理建议 |
|--------|------|------|----------|
| HighErrorRate | Warning | 错误率 > 5% | 检查应用日志 |
| CriticalErrorRate | Critical | 错误率 > 20% | 立即回滚或修复 |
| SlowResponseTime | Warning | P95 > 1s | 优化查询或扩容 |
| CriticalSlowResponseTime | Critical | P95 > 5s | 立即处理 |

---

## 运维操作

### 验证脚本

```bash
# 运行完整验证
./scripts/monitoring/verify.sh

# 包含 webhook 测试
WEBHOOK_URL=https://hooks.example.com/alerts ./scripts/monitoring/verify.sh --webhook-test
```

### 查看指标

```bash
# 直接查看指标
curl -s http://localhost:9091/metrics

# 查看特定指标
curl -s http://localhost:9091/metrics | grep journal_manager

# Prometheus 查询示例
curl -s 'http://localhost:9090/api/v1/query?query=up'
```

### 重启服务

```bash
# 重启 metrics-server
docker-compose restart metrics-server

# 重启整个监控栈
docker-compose restart prometheus grafana metrics-server

# 强制重新创建
docker-compose up -d --force-recreate metrics-server
```

### 数据保留

Prometheus 数据保留策略（30天）:
```yaml
# docker-compose.yml 中配置
command:
  - '--storage.tsdb.retention.time=30d'
```

手动清理旧数据:
```bash
# 进入 Prometheus 容器
docker exec -it opc200-prometheus sh

# 查看数据目录大小
du -sh /prometheus

# 删除旧数据（谨慎操作）
rm -rf /prometheus/*
```

---

## 故障排查

### Metrics Server 无响应

**症状**: curl http://localhost:9091/health 失败

**排查步骤**:
1. 检查容器状态: `docker-compose ps metrics-server`
2. 查看日志: `docker-compose logs metrics-server`
3. 检查端口占用: `lsof -i :9091`
4. 验证 Python 依赖: `docker exec opc200-metrics-server python -c "import monitoring.metrics"`

### Prometheus 抓取失败

**症状**: Targets 页面显示 DOWN

**排查步骤**:
1. 检查网络连通性: `docker exec opc200-prometheus wget -O- http://metrics-server:9091/metrics`
2. 验证配置: `docker exec opc200-prometheus promtool check config /etc/prometheus/prometheus.yml`
3. 检查防火墙规则

### Grafana 无数据

**症状**: 仪表板显示 "No data"

**排查步骤**:
1. 检查数据源配置: Configuration → Data Sources → Prometheus
2. 测试数据源: 点击 "Save & Test"
3. 检查查询语句: 在 Explore 页面手动执行查询
4. 验证时间范围: 确认选择的时间范围包含数据

### 告警不触发

**排查步骤**:
1. 检查告警规则: `docker exec opc200-prometheus promtool check rules /etc/prometheus/alerts.yml`
2. 查看告警状态: http://localhost:9090/alerts
3. 验证表达式: 在 Prometheus 查询页面测试告警表达式
4. 检查 Alertmanager 配置（如使用）

---

## 性能调优

### Metrics Server

```yaml
# docker-compose.yml
metrics-server:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
      reservations:
        cpus: '0.1'
        memory: 128M
```

### Prometheus

```yaml
# 优化抓取间隔
scrape_configs:
  - job_name: 'opc200-metrics'
    scrape_interval: 15s  # 高频指标
  
  - job_name: 'opc200-gateway'
    scrape_interval: 30s  # 低频指标

# 优化存储
command:
  - '--storage.tsdb.min-block-duration=2h'
  - '--storage.tsdb.max-block-duration=2h'
  - '--query.max-samples=50000000'
```

### Grafana

```yaml
# 缓存配置
environment:
  - GF_CACHE_ENABLED=true
  - GF_CACHE_TTL=300s
```

---

## 扩展阅读

- [Prometheus 查询语言 PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 仪表板文档](https://grafana.com/docs/grafana/latest/dashboards/)
- [OPC200 指标埋点指南](../src/monitoring/README.md)

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-02 | v2.3.0 | 初始版本，包含完整监控栈配置 |
