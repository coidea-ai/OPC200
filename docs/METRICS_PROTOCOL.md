# OPC200 指标推送协议

> 定义用户端 Agent 向平台端推送监控指标的标准规范

**版本**: v1.0.0  
**状态**: 初稿（待协商）  
**阻塞任务**: AGENT-005 (exporter 指标推送实现)

---

## 概述

用户端 Agent 通过 HTTPS 将监控指标推送到平台端的 Pushgateway，实现集中化监控。

**推送模式**:
- **单条推送**: 实时推送单个指标
- **批量推送**: 攒批后一次性推送多条指标（推荐，减少网络开销）

---

## Endpoint

### 基础 URL
```
https://platform.opc200.co/metrics/job/{tenant_id}
```

### 路径参数
| 参数 | 说明 | 示例 |
|------|------|------|
| `tenant_id` | 用户唯一标识 | `opc-001`, `opc-002` |

### 实例组（可选）
```
https://platform.opc200.co/metrics/job/{tenant_id}/instance/{instance_id}
```

### 完整示例
```
https://platform.opc200.co/metrics/job/opc-001
https://platform.opc200.co/metrics/job/opc-001/instance/macbook-pro-01
```

---

## 认证

使用 **Bearer Token** 进行认证。

### 请求头
```http
Authorization: Bearer {API_KEY}
Content-Type: text/plain
```

### API Key 获取
- 用户在平台端创建实例时生成
- 通过环境变量 `OPC200_API_KEY` 注入 Agent

---

## 指标格式

采用 **Prometheus Text Format**。

### Content-Type
```
text/plain; version=0.0.4
```

### 单行格式
```
metric_name{label1="value1",label2="value2"} value timestamp
```

### 必填元素
| 元素 | 说明 | 示例 |
|------|------|------|
| `metric_name` | 指标名称（下划线分隔） | `cpu_usage` |
| `labels` | 键值对标签 | `agent_version="1.0.0"` |
| `value` | 浮点数值 | `45.5` |
| `timestamp` | 毫秒时间戳（可选） | `1712736000000` |

### 重要规则
- **必须换行结尾**: 每行以 `\n` 结束
- **单条推送**: 1 行
- **批量推送**: 多行，每行 1 个指标

---

## 标准 Labels

所有指标必须包含以下标签：

| Label | 说明 | 示例 |
|-------|------|------|
| `tenant_id` | 用户标识（自动从 URL 注入） | `opc-001` |
| `agent_version` | Agent 版本号 | `1.0.0` |
| `os` | 操作系统 | `linux`, `darwin`, `windows` |

### 可选 Labels
| Label | 说明 | 示例 |
|-------|------|------|
| `arch` | 系统架构 | `amd64`, `arm64` |
| `hostname` | 主机名 | `macbook-pro` |

---

## 标准指标

### Gauge 类型（当前值）

| 指标名 | 类型 | 单位 | 说明 | 示例 |
|--------|------|------|------|------|
| `agent_health` | Gauge | 0/1 | Agent 健康状态（1=健康） | `1` |
| `cpu_usage` | Gauge | percent | CPU 使用率 | `45.5` |
| `memory_usage` | Gauge | percent | 内存使用率 | `78.2` |
| `disk_usage` | Gauge | percent | 磁盘使用率 | `65.0` |

### 指标示例

```
# 健康状态
agent_health{tenant_id="opc-001",agent_version="1.0.0",os="linux"} 1

# CPU 使用率
cpu_usage{tenant_id="opc-001",agent_version="1.0.0",os="linux"} 45.5

# 内存使用率
memory_usage{tenant_id="opc-001",agent_version="1.0.0",os="linux"} 78.2

# 磁盘使用率
disk_usage{tenant_id="opc-001",agent_version="1.0.0",os="linux"} 65.0
```

---

## 推送示例

### 单条推送

```bash
curl -X POST "https://platform.opc200.co/metrics/job/opc-001" \
  -H "Authorization: Bearer sk-opc200-xxxxxx" \
  -H "Content-Type: text/plain" \
  --data-binary 'cpu_usage{agent_version="1.0.0",os="linux"} 45.5
'
```

### 批量推送（推荐）

```bash
curl -X POST "https://platform.opc200.co/metrics/job/opc-001" \
  -H "Authorization: Bearer sk-opc200-xxxxxx" \
  -H "Content-Type: text/plain" \
  --data-binary 'agent_health{agent_version="1.0.0",os="linux"} 1
cpu_usage{agent_version="1.0.0",os="linux"} 45.5
memory_usage{agent_version="1.0.0",os="linux"} 78.2
disk_usage{agent_version="1.0.0",os="linux"} 65.0
'
```

---

## Python 示例

### 基础推送

```python
import requests
import time

class MetricsPusher:
    def __init__(self, platform_url: str, tenant_id: str, api_key: str):
        self.push_url = f"{platform_url}/metrics/job/{tenant_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "text/plain"
        }
        self.agent_version = "1.0.0"
        self.os = "linux"
    
    def push_single(self, metric_name: str, value: float, extra_labels: dict = None):
        """推送单个指标."""
        labels = f'agent_version="{self.agent_version}",os="{self.os}"'
        if extra_labels:
            for k, v in extra_labels.items():
                labels += f',{k}="{v}"'
        
        data = f'{metric_name}{{{labels}}} {value}\n'
        
        response = requests.post(
            self.push_url,
            headers=self.headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        return response
    
    def push_batch(self, metrics: list[dict]):
        """批量推送指标.
        
        metrics: [{"name": "cpu_usage", "value": 45.5}, ...]
        """
        lines = []
        for m in metrics:
            labels = f'agent_version="{self.agent_version}",os="{self.os}"'
            if "labels" in m:
                for k, v in m["labels"].items():
                    labels += f',{k}="{v}"'
            lines.append(f'{m["name"]}{{{labels}}} {m["value"]}')
        
        data = '\n'.join(lines) + '\n'
        
        response = requests.post(
            self.push_url,
            headers=self.headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        return response


# 使用示例
pusher = MetricsPusher(
    platform_url="https://platform.opc200.co",
    tenant_id="opc-001",
    api_key="sk-opc200-xxxxxx"
)

# 单条推送
pusher.push_single("cpu_usage", 45.5)

# 批量推送
pusher.push_batch([
    {"name": "agent_health", "value": 1},
    {"name": "cpu_usage", "value": 45.5},
    {"name": "memory_usage", "value": 78.2},
    {"name": "disk_usage", "value": 65.0},
])
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 含义 | 处理建议 |
|--------|------|----------|
| `200` | 成功 | - |
| `400` | 格式错误 | 检查指标格式，必须换行结尾 |
| `401` | 认证失败 | 检查 API Key 是否有效 |
| `404` | Endpoint 不存在 | 检查 tenant_id 是否正确 |
| `413` | 请求体过大 | 减少批量推送的指标数量 |
| `500` | 服务器错误 | 指数退避重试 |
| `503` | 服务不可用 | 指数退避重试 |

### 重试策略

采用**指数退避**算法：

```python
import time
import random

def exponential_backoff_retry(attempt):
    """计算重试延迟."""
    base_delay = 1  # 1 second
    max_delay = 60  # 60 seconds
    
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, 1)  # 添加抖动避免惊群
    
    return delay + jitter

# 使用示例
for attempt in range(5):
    try:
        push_metrics()
        break  # 成功，退出循环
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        delay = exponential_backoff_retry(attempt)
        time.sleep(delay)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [400, 401, 404]:
            raise  # 不重试客户端错误
        delay = exponential_backoff_retry(attempt)
        time.sleep(delay)
```

---

## 离线缓存（TODO - 待协商）

**待讨论事项**:

1. **缓存策略**
   - 断网时本地存储多久的数据？
   - 存储上限是多少（磁盘空间）？
   - 用什么格式存储（SQLite/文件队列）？

2. **恢复同步**
   - 网络恢复后一次性推送还是分批？
   - 如果缓存数据过多，优先推送最新的还是最旧的？
   - 数据过期策略（超过多久丢弃）？

3. **数据压缩**
   - 批量推送时是否启用 gzip？
   - 压缩阈值（多大才压缩）？

**相关方**: @zhang-yao-claw @zhang-chenyang-claw (用户侧 Agent 团队)

---

## 测试验证

### 验证步骤

1. **启动本地 Pushgateway**
   ```bash
   docker run -p 9091:9091 prom/pushgateway:v1.7.0
   ```

2. **推送测试指标**
   ```bash
   echo "test_metric 42" | curl -X POST \
     http://localhost:9091/metrics/job/test \
     --data-binary @-
   ```

3. **验证接收**
   ```bash
   curl http://localhost:9091/metrics | grep test_metric
   ```

---

## 变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-04-10 | 初稿 |

---

## 协作备注

**此文档阻塞 AGENT-005** (exporter 指标推送实现)

**待协商事项**:
1. **离线缓存机制**: 用户侧需要明确的缓存/恢复策略
2. **批量推送上限**: 单次最多推送多少条指标？
3. **推送频率**: 建议的采集间隔（15s/30s/60s）？

**协议位置**: `docs/METRICS_PROTOCOL.md`  
**测试位置**: `platform/tests/test_plat003_metrics_protocol.py`

如有问题请联系: @kimi-claw (平台侧)
