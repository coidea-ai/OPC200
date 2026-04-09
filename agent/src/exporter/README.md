# OPC Agent Exporter Module

## 功能

负责将 Agent 的指标推送到平台端的 Pushgateway。

## 组件

- `push_exporter.py`: 主推送逻辑
- `metrics_collector.py`: 指标收集器
- `config.py`: 推送配置

## 推送指标

- Agent 健康状态
- 资源使用情况 (CPU/内存/磁盘)
- Gateway 连接状态
- Journal 存储状态

## 协议

- Prometheus Pushgateway 协议
- HTTPS 出站连接
- 支持 tenant-id 标签区分客户
