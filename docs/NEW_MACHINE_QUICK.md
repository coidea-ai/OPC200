# OPC200 新机器部署 - 快速参考

## 🚀 最快方式（2分钟）

### 当前机器 - 导出（30秒）

```bash
# 运行导出脚本
bash scripts/deploy/export-package.sh

# 会生成: opc200-deploy-package.tar.gz
```

### 新机器 - 部署（90秒）

```bash
# 1. 复制文件（从当前机器）
scp opc200-deploy-package.tar.gz root@新机器IP:/root/

# 2. 登录新机器
ssh root@新机器IP

# 3. 解压并部署
tar xzvf opc200-deploy-package.tar.gz
cd opc200-deploy-package
bash setup.sh

# 完成！
```

---

## 📋 分步说明

### 方案1：有网络的新机器

```bash
# 新机器只需要这3行
curl -fsSL https://get.docker.com | sh
docker pull openclaw/gateway:2026.3  # 等等...
# 然后复制配置并部署
```

### 方案2：无网络的新机器（离线）

```bash
# 当前机器 - 导出含镜像的包
bash scripts/deploy/export-package.sh ./output true

# 复制到新机器（包较大，几百MB）
scp output.tar.gz root@新机器IP:/root/

# 新机器
bash load-images.sh  # 加载镜像
bash setup.sh        # 部署
```

### 方案3：手动复制配置

```bash
# 当前机器
cp .env /tmp/opc200.env
cp scripts/deploy/deploy-single.sh /tmp/

# 新机器
mkdir -p /opt/opc200
cp /tmp/opc200.env /opt/opc200/.env
# 安装Docker后
bash /tmp/deploy-single.sh
```

---

## 🎯 新机器检查清单

部署前确认：

- [ ] Linux系统（Ubuntu 22.04+ / CentOS 8+）
- [ ] RAM ≥ 8GB
- [ ] 磁盘 ≥ 50GB
- [ ] 端口 18789, 9090, 3000, 6333 可用
- [ ] 有网络（拉镜像）或已导入镜像

---

## 🔧 一键脚本（保存即用）

在新机器创建 `quick-setup.sh`：

```bash
#!/bin/bash
# OPC200 新机器一键部署

# 安装Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

# 拉取镜像
docker pull openclaw/gateway:2026.3
docker pull openclaw/agent:2026.3
docker pull qdrant/qdrant:v1.7.4
docker pull prom/prometheus:v2.49.1
docker pull grafana/grafana:10.3.1

# 准备配置
mkdir -p /opt/opc200
cat > /opt/opc200/.env << 'EOF'
APIATLAS_API_KEY=sk-your-key-here
INSTANCE_ID=opc-001
EOF

# 部署（需要deploy-single.sh在同一目录）
# bash deploy-single.sh

echo "Docker和镜像准备完成"
echo "请上传deploy-single.sh并执行部署"
```

---

## ❓ 常见问题

**Q: 新机器没有scp命令？**  
A: 用U盘、网盘、或者 `cat file | base64` 复制粘贴内容

**Q: 部署后访问不了？**  
A: 检查防火墙：`systemctl status firewalld` 或 `ufw status`

**Q: 怎么确认部署成功？**  
A: `curl http://127.0.0.1:18789/health` 返回200即成功

---

**一句话总结**：
> 运行 `export-package.sh` → 复制tar.gz到新机器 → 运行 `setup.sh` → 完成
