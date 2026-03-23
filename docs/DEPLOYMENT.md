# OPC200 部署指南

> **版本**: 2.2.0  
> **适用**: 本地部署 (150客户) + 云端托管 (50客户)

## 目录

1. [快速开始](#快速开始)
2. [本地部署](#本地部署)
3. [云端部署](#云端部署)
4. [Tailscale VPN 配置](#tailscale-vpn-配置)
5. [故障排除](#故障排除)

---

## 快速开始

### 前提条件

- Linux 服务器 (Ubuntu 22.04+ / Debian 12+)
- Docker 24.0+ 和 Docker Compose 2.20+
- 域名 (云端部署)
- Tailscale 账号 (本地部署)

### 一键部署脚本

```bash
# 1. 克隆仓库
git clone https://github.com/coidea-ai/OPC200.git
cd OPC200

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量

# 3. 启动服务
docker-compose up -d

# 4. 验证部署
./scripts/maintenance/health-check.sh
```

---

## 本地部署

### 架构概览

```
┌─────────────────────────────────────────┐
│          客户本地服务器                 │
│  ┌─────────────┐  ┌─────────────┐      │
│  │  Gateway    │  │   Journal   │      │
│  │  (Docker)   │  │  Service    │      │
│  └──────┬──────┘  └─────────────┘      │
│         │                               │
│  ┌──────┴──────────┐                   │
│  │  Tailscale VPN  │◄──── 支持中心     │
│  │  (WireGuard)    │      (经授权)     │
│  └─────────────────┘                   │
└─────────────────────────────────────────┘
```

### 详细步骤

#### 1. 环境准备

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 安装 Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
```

#### 2. 初始化客户

```bash
# 使用初始化脚本
./scripts/setup/customer-init.sh \
  -i OPC-001 \
  -m on-premise \
  -t "${TAILSCALE_AUTH_KEY}"
```

#### 3. 配置数据保险箱

```bash
# 设置数据保险箱密码
export OPC200_VAULT_PASSWORD=$(openssl rand -base64 32)

# 初始化加密存储
./scripts/setup/init-vault.sh \
  --path /data/opc200/vault \
  --password "${OPC200_VAULT_PASSWORD}"
```

#### 4. 启动服务

```bash
# 创建必要目录
mkdir -p /data/opc200/{journal,backups,logs}

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f gateway
```

#### 5. 验证 Tailscale 连接

```bash
# 检查 Tailscale 状态
tailscale status

# 测试与支持中心的连通性
ping support-hub.opc200.local
```

---

## 云端部署

### 架构概览

```
┌─────────────────────────────────────────┐
│           K8s 集群                      │
│  ┌─────────────┐  ┌─────────────┐      │
│  │  Gateway    │  │   Journal   │      │
│  │  (Pod)      │  │  Service    │      │
│  └──────┬──────┘  └─────────────┘      │
│         │                               │
│  ┌──────┴──────────┐                   │
│  │  Ingress/Nginx  │◄──── 客户访问     │
│  └─────────────────┘                   │
└─────────────────────────────────────────┘
```

### 使用 Helm 部署

```bash
# 添加 Helm 仓库
helm repo add opc200 https://charts.opc200.coidea.ai
helm repo update

# 安装
cat <<EOF | helm install opc200 opc200/opc200 -f -
gateway:
  replicaCount: 2
  ingress:
    enabled: true
    host: "opc-151.opc200.coidea.ai"
    
journal:
  persistence:
    enabled: true
    size: 100Gi
    
security:
  vault:
    enabled: true
EOF
```

### 使用 kubectl 部署

```bash
# 应用配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## Tailscale VPN 配置

### 1. 获取 Auth Key

```bash
# 在 Tailscale 控制台创建
# https://login.tailscale.com/admin/settings/keys

# 创建可重复使用的 key（用于自动化部署）
# 标签: tag:opc
```

### 2. 配置 ACL

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["group:support"],
      "dst": ["tag:opc:*"]
    },
    {
      "action": "deny",
      "src": ["tag:opc"],
      "dst": ["tag:opc"]
    }
  ],
  "tagOwners": {
    "tag:opc": ["group:support"]
  }
}
```

### 3. 客户端配置

```bash
# 启动 Tailscale
tailscale up --authkey "${TAILSCALE_AUTH_KEY}" --hostname "opc-001"

# 验证连接
tailscale status
```

---

## 故障排除

### 常见问题

#### 1. Gateway 无法启动

```bash
# 检查日志
docker-compose logs gateway

# 检查端口占用
sudo lsof -i :18789

# 检查配置文件语法
docker-compose config
```

#### 2. Tailscale 连接失败

```bash
# 重置 Tailscale
sudo tailscale down
sudo tailscale up --force-reauth

# 检查防火墙
sudo iptables -L | grep 41641

# 查看 Tailscale 日志
sudo journalctl -u tailscaled -f
```

#### 3. 数据保险箱访问失败

```bash
# 检查权限
ls -la /data/opc200/vault

# 验证密钥
docker-compose exec journal python -c "
from src.security.vault import SecureVault, VaultKeyManager
# 测试解密
"
```

#### 4. 性能问题

```bash
# 检查资源使用
docker stats

# 检查磁盘空间
df -h

# 清理日志
docker system prune -a
```

### 获取支持

- 文档: https://docs.opc200.coidea.ai
- 社区: https://community.opc200.coidea.ai
- 邮件: support@coidea.ai

---

## 参考

- [SYSTEM.md](../SYSTEM.md) - 架构设计
- [SECURITY.md](./SECURITY.md) - 安全指南
- [DEVELOPMENT.md](./DEVELOPMENT.md) - 开发指南
