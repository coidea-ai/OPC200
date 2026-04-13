# OPC200 新机器部署指南

## 📦 方案选择

### 方案A：复制配置部署（推荐）
如果当前机器已部署成功，直接复制配置文件到新机器：

```bash
# 当前机器 - 导出配置
mkdir -p ~/opc200-deploy
cp .env ~/opc200-deploy/
cp -r scripts/deploy ~/opc200-deploy/

# 打包（可选）
tar czvf opc200-deploy.tar.gz ~/opc200-deploy
```

```bash
# 新机器 - 导入并部署
scp opc200-deploy.tar.gz root@新机器IP:/root/
ssh root@新机器IP
tar xzvf opc200-deploy.tar.gz
cd opc200-deploy
bash deploy-single.sh
```

### 方案B：从头部署（新环境）
如果新机器是干净环境：

```bash
# 1. 安装Docker（如未安装）
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 2. 拉取项目（如果有Git仓库）
git clone https://github.com/coidea-ai/OPC200.git
cd OPC200

# 3. 或者手动创建配置
cat > .env << 'EOF'
APIATLAS_API_KEY=sk-your-key
INSTANCE_ID=opc-001
EOF

# 4. 部署
bash scripts/deploy/deploy-single.sh
```

---

## 🚀 推荐：一键迁移脚本

在当前机器运行：

```bash
# 导出部署包
bash scripts/deploy/export-for-new-machine.sh 新机器IP

# 这会：
# 1. 打包当前配置
# 2. 上传到目标机器
# 3. 自动在新机器执行部署
```

---

## 📋 新机器检查清单

### 硬件要求
- [ ] RAM: 8GB+ (建议16GB)
- [ ] Disk: 50GB+ 可用空间
- [ ] CPU: 4核+

### 软件环境
- [ ] Docker 24.0+
- [ ] Docker Compose 2.20+
- [ ] curl, ss 等基础工具

### 网络要求
- [ ] 可访问外网（拉取镜像）
- [ ] 端口未占用：18789, 9090, 3000, 6333
- [ ] 如需远程访问，防火墙开放相应端口

---

## 🔧 快速部署命令（复制即用）

在新机器执行：

```bash
#!/bin/bash
# 新机器一键部署脚本 - 保存为 setup-new-machine.sh

set -e

echo "=== OPC200 新机器部署 ==="

# 1. 检查Docker
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

# 2. 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose未安装"
    exit 1
fi

# 3. 创建目录
mkdir -p /opt/opc200

# 4. 获取配置（以下二选一）

# 方式1：手动填写（交互式）
read -p "请输入APIATLAS_API_KEY: " API_KEY
cat > /opt/opc200/.env << EOF
APIATLAS_API_KEY=$API_KEY
INSTANCE_ID=opc-001
EOF

# 5. 拉取部署脚本
# 方式1：从GitHub
# curl -O https://raw.githubusercontent.com/coidea-ai/OPC200/main/scripts/deploy/deploy-single.sh

# 方式2：本地已有（从当前机器复制过来）
# 假设脚本已在 /root/opc200-deploy/

# 6. 执行部署
cd /opt/opc200
bash deploy-single.sh

# 7. 启动
cd /opt/opc200/opc-001
docker-compose up -d

echo "部署完成！"
echo "Gateway: http://$(hostname -I | awk '{print $1}'):18789"
```

---

## 📤 从当前机器复制到新机器

### 步骤1：当前机器 - 打包

```bash
# 方法1：仅打包配置（推荐，脚本从GitHub拉）
mkdir -p ~/opc200-export
cp .env ~/opc200-export/
cd ~ && tar czvf opc200-config.tar.gz opc200-export

# 方法2：打包全部（包括脚本）
mkdir -p ~/opc200-full
cp .env ~/opc200-full/
cp -r scripts/deploy ~/opc200-full/
tar czvf opc200-full.tar.gz opc200-full
```

### 步骤2：传输到新机器

```bash
# 使用scp
scp opc200-full.tar.gz root@新机器IP:/root/

# 或使用rsync（更稳定）
rsync -avz opc200-full.tar.gz root@新机器IP:/root/
```

### 步骤3：新机器 - 部署

```bash
ssh root@新机器IP
tar xzvf opc200-full.tar.gz
cd opc200-full

# 安装Docker（如需要）
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 部署
bash deploy-single.sh

# 启动
cd /opt/opc200/opc-001
docker-compose up -d
```

---

## 🔄 多机器批量部署

如果需要部署多台机器（如给客户批量部署）：

```bash
# machines.txt 格式: IP 实例ID
# 192.168.1.101 opc-001
# 192.168.1.102 opc-002

cat machines.txt | while read IP INSTANCE; do
    echo "部署到 $IP ($INSTANCE)..."
    
    # 复制配置
    scp .env root@$IP:/tmp/opc200.env
    
    # 远程执行部署
    ssh root@$IP "
        mkdir -p /opt/opc200
        curl -fsSL https://get.docker.com | sh 2>/dev/null || true
        systemctl start docker
        # 这里需要有部署脚本...
    "
done
```

---

## 📋 新机器部署检查表

部署完成后验证：

```bash
# 1. 检查容器运行
docker ps

# 2. 检查服务健康
curl http://127.0.0.1:18789/health
curl http://127.0.0.1:6333/healthz

# 3. 检查日志
cd /opt/opc200/opc-001
docker-compose logs

# 4. 资源检查
free -h
df -h
```

---

## 💡 最佳实践

### 1. 使用配置版本控制
```bash
# 将.env纳入Git管理（不要提交到公开仓库）
git init
git add .env.single.template scripts/deploy/
git commit -m "OPC200部署配置"

# 新机器直接拉取
git clone your-repo.git
cd OPC200
cp .env.single.template .env
# 编辑.env填入API Key
bash scripts/deploy/deploy-single.sh
```

### 2. 使用Docker Registry镜像
如果客户机器无法访问Docker Hub：
```bash
# 有网络机器：导出镜像
docker save openclaw/gateway:2026.3 > gateway.tar
docker save openclaw/agent:2026.3 > agent.tar

# 无网络机器：导入镜像
docker load < gateway.tar
docker load < agent.tar
```

### 3. 使用安装向导脚本
提供一个统一的入口脚本：
```bash
curl -fsSL https://your-domain.com/install-opc200.sh | bash
```

---

## ❓ 常见问题

### Q: 新机器没有外网怎么办？
A: 
1. 在有网机器下载镜像: `docker pull` + `docker save`
2. 复制镜像tar包到新机器
3. 新机器`docker load`导入
4. 同样方式处理部署脚本

### Q: 如何快速复制已配置好的实例？
A:
```bash
# 打包整个实例目录
tar czvf opc001-backup.tar.gz /opt/opc200/opc-001

# 新机器解压即可用（无需重新部署）
tar xzvf opc001-backup.tar.gz -C /
cd /opt/opc200/opc-001 && docker-compose up -d
```

### Q: 多个客户机器配置不同怎么办？
A: 为每个客户生成独立的.env文件：
```bash
# 生成客户A的配置
INSTANCE_ID=opc-a001 APIATLAS_API_KEY=sk-xxx bash -c '
cat > .env.${INSTANCE_ID} << EOF
INSTANCE_ID=${INSTANCE_ID}
APIATLAS_API_KEY=${APIATLAS_API_KEY}
GATEWAY_PORT=18789
EOF
'
```

---

**版本**: v1.0  
**更新**: 2026-04-07
