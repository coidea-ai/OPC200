# OPC200 监控栈本地部署指南

> **适用场景**: 在本地电脑（Mac/Windows/Linux）部署完整的 OPC200 监控栈  
> **部署版本**: v2.3.0  
> **预计时间**: 15-20 分钟  
> **难度**: ⭐⭐⭐ 中等

---

## 📋 前置要求

### 系统要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB 可用空间 | 20 GB |
| 网络 | 可访问互联网 | - |

### 操作系统支持

- ✅ macOS 11+ (Intel/Apple Silicon)
- ✅ Windows 10/11 (WSL2 或 Git Bash)
- ✅ Ubuntu 20.04/22.04/24.04
- ✅ CentOS 7/8
- ✅ Debian 10/11/12

---

## 🔧 第一步：环境准备

### 1.1 安装基础工具

#### macOS

```bash
# 安装 Homebrew (如果未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装基础工具
brew install wget curl python3

# 验证安装
python3 --version  # 需要 3.10+
wget --version
curl --version
```

#### Ubuntu/Debian

```bash
# 更新系统
sudo apt-get update

# 安装基础工具
sudo apt-get install -y wget curl python3 python3-pip

# 验证安装
python3 --version  # 需要 3.10+
wget --version
curl --version
```

#### CentOS/RHEL

```bash
# 安装基础工具
sudo yum install -y wget curl python3 python3-pip

# 验证安装
python3 --version
```

#### Windows (WSL2)

```bash
# 在 WSL2 Ubuntu 中执行
sudo apt-get update
sudo apt-get install -y wget curl python3 python3-pip
```

---

## 📥 第二步：下载软件包

创建一个工作目录：

```bash
# 创建工作目录
mkdir -p ~/opc200-monitoring
cd ~/opc200-monitoring

# 创建子目录
mkdir -p prometheus grafana alertmanager node_exporter
```

### 2.1 下载 Prometheus

```bash
cd ~/opc200-monitoring

# macOS (Intel)
wget https://github.com/prometheus/prometheus/releases/download/v2.49.1/prometheus-2.49.1.darwin-amd64.tar.gz

# macOS (Apple Silicon M1/M2)
wget https://github.com/prometheus/prometheus/releases/download/v2.49.1/prometheus-2.49.1.darwin-arm64.tar.gz

# Linux (AMD64)
wget https://github.com/prometheus/prometheus/releases/download/v2.49.1/prometheus-2.49.1.linux-amd64.tar.gz

# Linux (ARM64)
wget https://github.com/prometheus/prometheus/releases/download/v2.49.1/prometheus-2.49.1.linux-arm64.tar.gz

# 解压
tar xzf prometheus-*.tar.gz
mv prometheus-2.49.1.* prometheus
```

### 2.2 下载 node_exporter

```bash
cd ~/opc200-monitoring

# macOS (Intel)
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.darwin-amd64.tar.gz

# macOS (Apple Silicon)
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.darwin-arm64.tar.gz

# Linux (AMD64)
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz

# Linux (ARM64)
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-arm64.tar.gz

# 解压
tar xzf node_exporter-*.tar.gz
mv node_exporter-1.7.0.* node_exporter
```

### 2.3 下载 Grafana

```bash
cd ~/opc200-monitoring

# macOS (Intel)
wget https://dl.grafana.com/oss/release/grafana-10.3.1.darwin-amd64.tar.gz

# macOS (Apple Silicon)
wget https://dl.grafana.com/oss/release/grafana-10.3.1.darwin-arm64.tar.gz

# Linux (AMD64)
wget https://dl.grafana.com/oss/release/grafana-10.3.1.linux-amd64.tar.gz

# Linux (ARM64)
wget https://dl.grafana.com/oss/release/grafana-10.3.1.linux-arm64.tar.gz

# 解压
tar xzf grafana-*.tar.gz
mv grafana-10.3.1 grafana
```

### 2.4 下载 Alertmanager

```bash
cd ~/opc200-monitoring

# macOS (Intel)
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.darwin-amd64.tar.gz

# macOS (Apple Silicon)
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.darwin-arm64.tar.gz

# Linux (AMD64)
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.linux-amd64.tar.gz

# Linux (ARM64)
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.linux-arm64.tar.gz

# 解压
tar xzf alertmanager-*.tar.gz
mv alertmanager-0.26.0.* alertmanager
```

### 2.5 验证下载

```bash
cd ~/opc200-monitoring
ls -la

# 应该看到:
# alertmanager/
# grafana/
# node_exporter/
# prometheus/
```

---

## ⚙️ 第三步：配置监控组件

### 3.1 配置 Prometheus

创建配置文件：

```bash
cat > ~/opc200-monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'opc200'

# Alertmanager 配置
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

# 告警规则文件
rule_files:
  - "alerts.yml"

# 抓取目标配置
scrape_configs:
  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # OPC200 Metrics Server
  - job_name: 'opc200-metrics'
    static_configs:
      - targets: ['localhost:9091']
    metrics_path: /metrics
    scrape_interval: 15s

  # 系统指标 (node_exporter)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
EOF
```

### 3.2 创建告警规则

```bash
cat > ~/opc200-monitoring/prometheus/alerts.yml << 'EOF'
groups:
  - name: opc200-service-alerts
    interval: 30s
    rules:
      # 服务可用性告警
      - alert: OPC200MetricsServerDown
        expr: up{job="opc200-metrics"} == 0
        for: 1m
        labels:
          severity: critical
          service: metrics-server
        annotations:
          summary: "OPC200 Metrics Server is down"
          description: "Metrics server has been down for more than 1 minute."

      # 磁盘使用告警
      - alert: HighDiskUsage
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 80
        for: 5m
        labels:
          severity: warning
          resource: disk
        annotations:
          summary: "Disk usage is above 80%"
          description: "Disk usage is {{ $value | humanize }}%"

      # 内存使用告警
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: warning
          resource: memory
        annotations:
          summary: "Memory usage is above 90%"
          description: "Memory usage is {{ $value | humanize }}%"
EOF
```

### 3.3 配置 Alertmanager

```bash
cat > ~/opc200-monitoring/alertmanager/alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alert@opc200.local'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'webhook'

receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF
```

### 3.4 配置 Grafana

```bash
# 创建 Grafana 数据源配置
mkdir -p ~/opc200-monitoring/grafana/conf/provisioning/datasources

cat > ~/opc200-monitoring/grafana/conf/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
EOF
```

---

## 🚀 第四步：启动监控栈

### 4.1 启动 node_exporter

```bash
cd ~/opc200-monitoring/node_exporter

# 启动
./node_exporter --web.listen-address=:9100 &

# 验证
curl http://localhost:9100/metrics | head
```

### 4.2 启动 Prometheus

```bash
cd ~/opc200-monitoring/prometheus

# 创建数据目录
mkdir -p data

# 启动
./prometheus \
  --config.file=prometheus.yml \
  --storage.tsdb.path=./data \
  --web.enable-lifecycle &

# 验证
curl http://localhost:9090/-/healthy
```

### 4.3 启动 Alertmanager

```bash
cd ~/opc200-monitoring/alertmanager

# 启动
./alertmanager \
  --config.file=alertmanager.yml \
  --web.listen-address=:9093 &

# 验证
curl http://localhost:9093/-/healthy
```

### 4.4 启动 Grafana

```bash
cd ~/opc200-monitoring/grafana

# 启动 (macOS/Linux 略有不同)
# macOS
./bin/grafana-server &

# Linux
./bin/grafana-server --config=conf/defaults.ini &

# 等待启动
sleep 5

# 验证
curl http://localhost:3000/api/health
```

---

## 🧪 第五步：验证测试

### 5.1 检查所有服务状态

```bash
echo "=== 服务状态检查 ==="

check_service() {
    name=$1
    url=$2
    if curl -s "$url" > /dev/null 2>&1; then
        echo "✅ $name: 运行正常"
    else
        echo "❌ $name: 未运行"
    fi
}

check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "node_exporter" "http://localhost:9100/metrics"
check_service "Alertmanager" "http://localhost:9093/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"
```

### 5.2 查看告警规则

打开浏览器访问: http://localhost:9090/rules

应该看到:
- OPC200MetricsServerDown
- HighDiskUsage
- HighMemoryUsage

### 5.3 测试告警触发

**测试 MetricsServerDown 告警**:

```bash
# 1. 创建一个模拟的 metrics server
python3 << 'PYEOF'
import http.server
import socketserver

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'# HELP test_metric Test metric\n# TYPE test_metric gauge\ntest_metric 1\n')

httpd = socketserver.TCPServer(("", 9091), Handler)
print("Metrics server on port 9091")
httpd.serve_forever()
PYEOF
```

然后在另一个终端:

```bash
# 停止服务 (模拟故障)
pkill -f "python3.*9091"

# 等待 1 分钟
sleep 65

# 检查告警状态
curl http://localhost:9090/api/v1/rules | python3 -m json.tool

# 应该会看到 OPC200MetricsServerDown 状态为 "firing"
```

### 5.4 访问 Grafana

1. 打开浏览器: http://localhost:3000
2. 登录: admin / admin
3. 首次登录会要求修改密码
4. 进入 Explore → 选择 Prometheus 数据源
5. 查询测试: `up`

---

## 📊 第六步：导入 OPC200 仪表板

### 6.1 创建自定义仪表板

在 Grafana 中:
1. 点击左侧 "+" → "Dashboard"
2. 点击 "Add visualization"
3. 选择 Prometheus 数据源
4. 输入查询: `up`
5. 保存仪表板

### 6.2 常用查询语句

```promql
# 服务状态
up{job="opc200-metrics"}

# CPU 使用率
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
```

---

## 🔧 第七步：配置告警通知 (可选)

### 7.1 配置飞书 Webhook

修改 `~/opc200-monitoring/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'feishu'
    webhook_configs:
      - url: 'https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN'
        send_resolved: true
```

然后重载配置:

```bash
curl -X POST http://localhost:9093/-/reload
```

### 7.2 配置钉钉 Webhook

```yaml
receivers:
  - name: 'dingtalk'
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN'
        send_resolved: true
```

---

## 🛑 第八步：停止服务

当需要停止监控栈时:

```bash
# 停止所有组件
pkill -f prometheus
pkill -f node_exporter
pkill -f alertmanager
pkill -f grafana-server

# 或者单独停止
pkill -f prometheus
```

---

## 🔄 第九步：日常运维

### 9.1 重启服务

```bash
cd ~/opc200-monitoring

# 重启 Prometheus
pkill -f prometheus
./prometheus/prometheus --config.file=prometheus/prometheus.yml &

# 重启其他组件类似...
```

### 9.2 查看日志

```bash
# Prometheus 日志在控制台输出
# 如需保存到文件:
./prometheus --config.file=prometheus.yml > prometheus.log 2>&1 &

# 查看日志
tail -f prometheus.log
```

### 9.3 数据备份

```bash
# 备份 Prometheus 数据
tar czf prometheus-backup-$(date +%Y%m%d).tar.gz ~/opc200-monitoring/prometheus/data/

# 备份配置
tar czf prometheus-config-$(date +%Y%m%d).tar.gz ~/opc200-monitoring/prometheus/*.yml
```

---

## ❓ 常见问题

### Q1: 端口被占用

```bash
# 查找占用端口的进程
lsof -i :9090  # macOS/Linux
netstat -ano | findstr :9090  # Windows

# 更换端口启动
./prometheus --web.listen-address=:9092
```

### Q2: Prometheus 启动失败

```bash
# 检查配置文件语法
./promtool check config prometheus.yml

# 检查规则文件语法
./promtool check rules alerts.yml
```

### Q3: Grafana 无法访问

```bash
# 检查 Grafana 日志
cat ~/opc200-monitoring/grafana/data/log/grafana.log

# 重置管理员密码
./grafana-cli admin reset-admin-password admin
```

### Q4: 告警不触发

```bash
# 检查告警规则是否加载
curl http://localhost:9090/api/v1/rules

# 检查告警表达式
curl 'http://localhost:9090/api/v1/query?query=up'
```

---

## 📚 参考资源

- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [Alertmanager 文档](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [node_exporter 文档](https://github.com/prometheus/node_exporter)

---

## ✅ 部署检查清单

- [ ] 下载所有软件包
- [ ] 配置 Prometheus
- [ ] 配置告警规则
- [ ] 配置 Alertmanager
- [ ] 配置 Grafana
- [ ] 启动所有服务
- [ ] 验证服务状态
- [ ] 测试告警触发
- [ ] 访问 Grafana
- [ ] 创建仪表板

**全部勾选完成即部署成功！** 🎉

---

*文档版本: v1.0*  
*更新日期: 2026-04-07*  
*作者: OpenClaw Agent*
