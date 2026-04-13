# OPC Platform (平台侧)

OPC200 云端平台组件，负责集中监控、版本管理和告警通知。

## 目录结构

```
platform/
├── pushgateway/           # 指标接收服务
├── prometheus/            # 时序数据存储
├── grafana/               # 可视化 Dashboard
├── alertmanager/          # 告警路由
└── version-control/       # 版本管理 + 灰度发布
```

## 构建

```bash
cd platform
docker-compose up -d
```

## 服务清单

| 服务 | 端口 | 说明 |
|------|------|------|
| Pushgateway | 9091 | 接收 Agent 推送的指标 |
| Prometheus | 9090 | 时序数据库 |
| Grafana | 3000 | 可视化面板 |
| AlertManager | 9093 | 告警管理 |
| Version Control | 8080 | 版本管理服务 |
