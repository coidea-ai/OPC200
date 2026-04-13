# OPC Agent Gateway Module

## 功能

精简版 OpenClaw Gateway，仅保留核心对话功能。

## 与原版的区别

| 组件 | 原版 Gateway | 精简版 Gateway |
|------|-------------|---------------|
| 对话核心 | ✅ 保留 | ✅ 保留 |
| Skills 加载 | ✅ 保留 | ✅ 保留 |
| 内置 Prometheus | ✅ 有 | ❌ 移除（移到平台端）|
| 内置 Grafana | ✅ 有 | ❌ 移除（移到平台端）|
| 指标推送 | ❌ 无 | ✅ 新增（通过 Exporter）|

## 配置

使用 `agent/config/gateway.yml` 作为配置文件，去除监控相关配置。
