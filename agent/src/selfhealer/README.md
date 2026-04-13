# OPC Agent Self-Healer Module

## 功能

三级自修复机制，保障 Agent 7×24 小时服务可用性。

## 组件

- `l1_local_fix.py`: L1 本地自动修复（秒级）
- `l2_ai_diagnose.py`: L2 AI 诊断修复（分钟级）
- `l3_alert.py`: L3 告警通知（人工介入）
- `recovery.py`: 恢复出厂设置

## L1 自动修复场景

- Gateway 进程崩溃 → 自动重启
- 内存泄漏 → 优雅重启
- 磁盘空间不足 → 清理旧日志
- 配置损坏 → 回滚到上一个有效配置

## L2 AI 诊断场景

- 服务无响应
- 网络连接异常
- 数据不一致
