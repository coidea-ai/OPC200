# OPC200 单实例部署指南

## 📋 概述

本指南用于部署**一套完整**的OPC200实例。部署完成后，如需更多实例，可使用扩展脚本快速部署。

## 🚀 快速开始（3步）

### 第1步：准备配置

```bash
# 复制配置模板
cp .env.single.template .env

# 编辑配置（只需填API Key）
vi .env
```

**最小配置示例**（仅需修改API Key）：
```bash
APIATLAS_API_KEY=sk-your-api-key-from-apiatlas
```

如需修改端口或其他配置，参考模板中的注释。

### 第2步：执行部署

```bash
bash scripts/deploy/deploy-single.sh
```

部署脚本会：
1. 验证配置
2. 创建目录结构
3. 生成模型配置（中转站API）
4. 生成Docker Compose
5. 设置权限
6. 输出访问信息

### 第3步：启动服务

```bash
# 进入实例目录
cd /opt/opc200/opc-001

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```

## ✅ 验证部署

```bash
# 运行验证脚本
bash scripts/deploy/validate-single.sh

# 预期输出:
# [✓] 目录结构正确
# [✓] 配置文件存在
# [✓] Docker Compose配置有效
# [✓] 容器运行中
# [✓] Gateway健康
# ...
# 所有检查通过!
```

## 🌐 访问服务

部署完成后，可通过以下地址访问：

| 服务 | 地址 | 认证 |
|------|------|------|
| Gateway | http://127.0.0.1:18789 | Token |
| Grafana | http://127.0.0.1:3000 | admin/admin-opc-001 |
| Prometheus | http://127.0.0.1:9090 | 无 |
| Qdrant | http://127.0.0.1:6333 | 无 |

## 📁 目录结构

```
/opt/opc200/opc-001/
├── docker-compose.yml       # Docker编排配置
├── config/
│   ├── models.json         # 中转站模型配置
│   ├── prometheus.yml      # 监控配置
│   ├── gateway-token.txt   # Gateway认证Token
│   └── deploy-info.txt     # 部署信息
├── data/
│   ├── gateway/            # Gateway数据
│   ├── journal/            # Journal数据
│   └── qdrant/             # 向量数据库
└── logs/                   # 日志文件
```

## 🔧 常用命令

### 服务管理
```bash
cd /opt/opc200/opc-001

# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f gateway
```

### 验证测试
```bash
# 测试Gateway
curl http://127.0.0.1:18789/health

# 测试Qdrant
curl http://127.0.0.1:6333/healthz

# 完整验证
bash scripts/deploy/validate-single.sh
```

## 📈 扩展部署

第一个实例部署完成后，可使用扩展脚本部署更多实例：

```bash
# 交互式部署第二个实例
bash scripts/deploy/extend-instance.sh

# 输入:
#   新实例ID: opc-002
#   端口偏移: 1 (自动计算为18790/9091/3001...)

# 或使用生成的配置文件手动部署
bash scripts/deploy/deploy-single.sh .env.opc-002
```

### 批量管理（多实例）

```bash
# 启动所有实例
for d in /opt/opc200/opc-*; do (cd $d && docker-compose up -d); done

# 停止所有实例
for d in /opt/opc200/opc-*; do (cd $d && docker-compose down); done

# 查看所有实例状态
for d in /opt/opc200/opc-*; do echo "=== $(basename $d) ===" && (cd $d && docker-compose ps); done
```

## ⚙️ 配置说明

### 必填项

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `APIATLAS_API_KEY` | 中转站API Key | https://api.apiatlas.com |
| `GATEWAY_TOKEN` | Gateway认证Token | 自动生成或手动设置 |
| `GRAFANA_PASSWORD` | Grafana管理员密码 | 建议修改默认值 |

### 端口配置

| 端口 | 服务 | 默认 |
|------|------|------|
| `GATEWAY_PORT` | Gateway | 18789 |
| `PROMETHEUS_PORT` | Prometheus | 9090 |
| `GRAFANA_PORT` | Grafana | 3000 |
| `QDRANT_PORT` | Qdrant | 6333 |

如需修改，编辑 `.env` 后重新运行部署脚本。

### 网络配置

- `BIND_ADDRESS=127.0.0.1` - 仅本机访问（安全）
- `BIND_ADDRESS=0.0.0.0` - 全网可访问（需防火墙配置）

## 🆘 故障排查

### 问题1: 端口被占用

```bash
# 检查端口占用
sudo ss -tlnp | grep 18789

# 解决: 修改.env中的端口配置
vi .env
# 修改 GATEWAY_PORT=18790

# 重新部署
bash scripts/deploy/deploy-single.sh
```

### 问题2: 容器无法启动

```bash
# 查看日志
cd /opt/opc200/opc-001
docker-compose logs

# 常见问题:
# - 端口冲突
# - 磁盘空间不足
# - 镜像拉取失败
```

### 问题3: Gateway无法连接

```bash
# 检查服务状态
curl http://127.0.0.1:18789/health

# 检查日志
docker-compose logs gateway

# 检查模型配置
cat config/models.json | grep baseUrl
```

### 问题4: 模型API报错

```bash
# 检查API Key
cat .env | grep APIATLAS_API_KEY

# 测试中转站连通性
curl -H "Authorization: Bearer $APIATLAS_API_KEY" \
  https://api.apiatlas.com/v1/models
```

## 📝 完整示例

```bash
# 1. 准备目录
cd /path/to/OPC200

# 2. 复制配置
cp .env.single.template .env

# 3. 填写API Key
echo 'APIATLAS_API_KEY=sk-your-key' >> .env

# 4. 部署
bash scripts/deploy/deploy-single.sh

# 5. 启动
cd /opt/opc200/opc-001 && docker-compose up -d

# 6. 验证
bash scripts/deploy/validate-single.sh

# 7. 测试访问
curl http://127.0.0.1:18789/health
```

## 📚 相关文档

- [5实例部署方案](DEPLOYMENT_5_INSTANCES.md) - 多实例架构详情
- [配置模板](../.env.single.template) - 完整配置选项
- [运维速查卡](5_INSTANCES_CHEATSHEET.md) - 常用命令

---

**版本**: v1.0  
**更新**: 2026-04-07
