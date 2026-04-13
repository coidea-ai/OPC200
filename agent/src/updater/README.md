# OPC Agent Updater Module

## 功能

Agent 版本更新客户端，支持从平台端拉取新版本。

## 组件

- `update_client.py`: 更新客户端主逻辑
- `version_checker.py`: 版本检查器
- `download_manager.py`: 下载管理器
- `verify.py`: 签名验证

## 更新策略

- **长轮询**: Agent 每5分钟检查更新
- **WebSocket**: 实时推送紧急更新
- **灰度发布**: 支持渐进式更新
- **签名验证**: 所有更新包强制签名验证

## 更新模式

- `auto`: 自动下载并安装
- `manual`: 仅通知，用户手动确认
- `scheduled`: 定时更新（如凌晨3点）
