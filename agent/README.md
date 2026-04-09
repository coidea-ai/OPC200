# OPC Agent (用户侧)

OPC200 用户端部署组件，为单个用户提供轻量级 AI 助手服务。

## 目录结构

```
agent/
├── src/                    # 源代码
│   ├── gateway/           # 精简版 OpenClaw Gateway
│   ├── journal/           # 本地 SQLite 存储
│   ├── exporter/          # 指标推送到平台
│   ├── selfhealer/        # 自修复机制
│   └── updater/           # 版本更新客户端
├── config/                # 配置文件
├── skills/                # 用户侧 Skills
└── scripts/               # 安装/卸载脚本
```

## 构建

```bash
cd agent
docker build -t opc-agent:latest .
```

## 运行

```bash
docker run -d \
  --name opc-agent \
  -v ~/.opc200:/data \
  -e PLATFORM_URL=https://opc200.co \
  -e CUSTOMER_ID=opc-001 \
  -e API_KEY=sk-xxx \
  opc-agent:latest
```
