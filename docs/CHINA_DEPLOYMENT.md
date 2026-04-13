# OPC200 国内网络部署指南

## 🎯 问题背景

国内用户部署时常见网络问题：
- Docker Hub 连接超时
- 镜像拉取速度慢或失败
- 无梯子环境无法部署

## ✅ 解决方案

### 方案1：国内镜像源（推荐，有网络）

部署前配置Docker使用国内镜像源：

```bash
# 1. 运行国内镜像配置脚本
bash scripts/deploy/setup-china-mirror.sh

# 2. 拉取镜像
opc200-pull-images

# 3. 执行部署
bash setup.sh
```

**配置的镜像源**：
- Docker.1Panel (推荐)
- DaoCloud
- DockerProxy
- 中科大
- 南京大学
- 百度云
- 上海交大

---

### 方案2：离线部署（推荐，无网络）

在**有网络的机器**导出含镜像的包：

```bash
# 当前机器（有网络）
bash scripts/deploy/export-offline-package.sh ./opc200-offline

# 会生成: opc200-offline.tar.gz（约2-3GB）
```

传输到**目标机器**（无网络）：

```bash
# 复制到目标机器（用U盘/内网传）
scp opc200-offline.tar.gz root@目标机器:/root/

# 目标机器部署
ssh root@目标机器
tar xzvf opc200-offline.tar.gz
cd opc200-offline
sudo bash setup-offline.sh
```

**离线包内容**：
```
opc200-offline/
├── images/              # Docker镜像（.tar格式）
│   ├── openclaw_gateway_2026.3.tar
│   ├── openclaw_agent_2026.3.tar
│   └── ...
├── scripts/             # 部署脚本
├── .env                 # 配置文件
├── load-images.sh       # 镜像加载脚本
└── setup-offline.sh     # 离线部署脚本
```

**离线部署要求**：
- [x] 目标机器已安装Docker
- [x] 磁盘空间 ≥ 10GB
- [ ] 无需网络连接

---

### 方案3：混合部署（部分离线）

如果只有部分镜像无法下载：

```bash
# 1. 有网机器下载缺失镜像
docker pull openclaw/gateway:2026.3
docker save openclaw/gateway:2026.3 > gateway.tar

# 2. 复制到目标机器
scp gateway.tar root@目标机器:/root/

# 3. 目标机器加载
docker load < gateway.tar

# 4. 正常部署
bash setup.sh
```

---

## 📋 快速决策

| 你的情况 | 推荐方案 | 命令 |
|---------|---------|------|
| 有网络，无梯子 | 方案1：国内镜像源 | `setup-china-mirror.sh` |
| 无网络 | 方案2：离线部署 | `export-offline-package.sh` |
| 只有部分镜像下不了 | 方案3：混合部署 | 手动导出/加载 |

---

## 🔧 详细步骤

### 方案1：国内镜像源（详细）

```bash
# 步骤1：配置镜像源
sudo bash scripts/deploy/setup-china-mirror.sh

# 输出示例：
# [✓] Docker镜像源配置完成
# [✓] 镜像源配置已生效
#   Registry Mirrors:
#     https://docker.1panel.live/
#     https://docker.m.daocloud.io/
# ...

# 步骤2：测试拉取
opc200-pull-images

# 步骤3：部署
bash scripts/deploy/deploy-single.sh
cd /opt/opc200/opc-001 && docker-compose up -d
```

**镜像源配置文件位置**：
```bash
/etc/docker/daemon.json
```

**手动修改**（如脚本执行失败）：
```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://docker.m.daocloud.io"
  ]
}
EOF
systemctl restart docker
```

---

### 方案2：离线部署（详细）

**准备阶段（有网络机器）**：

```bash
# 1. 确保镜像已下载
docker pull openclaw/gateway:2026.3
docker pull openclaw/agent:2026.3
docker pull qdrant/qdrant:v1.7.4
docker pull prom/prometheus:v2.49.1
docker pull grafana/grafana:10.3.1

# 2. 导出离线包
bash scripts/deploy/export-offline-package.sh ./my-opc200-package

# 3. 传输到目标机器
scp my-opc200-package.tar.gz user@目标机器:/root/
# 或使用U盘、内网文件传输工具
```

**部署阶段（无网络机器）**：

```bash
# 1. 解压
tar xzvf my-opc200-package.tar.gz
cd my-opc200-package

# 2. 配置（如需要）
cp .env.example .env
vi .env  # 填写API Key

# 3. 执行离线部署
sudo bash setup-offline.sh

# 输出示例：
# [1/4] 检查Docker... [✓]
# [2/4] 加载Docker镜像... [✓]
# [3/4] 检查配置... [✓]
# [4/4] 执行部署... [✓]
# 离线部署成功!
```

---

## 🆘 故障排查

### 问题1：国内镜像源仍无法拉取

**现象**：配置了镜像源，但还是timeout

**解决**：
```bash
# 检查配置是否生效
docker info | grep -A 10 "Registry Mirrors"

# 如果为空，手动配置
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://docker.1panel.live"]
}
EOF
systemctl restart docker

# 如仍不行，尝试其他源
# https://docker.m.daocloud.io
# https://dockerproxy.com
```

### 问题2：离线包太大传不了

**现象**：tar.gz包2-3GB，传输困难

**解决**：
```bash
# 方法1：分卷压缩
tar czvf - opc200-offline | split -b 500M - opc200-offline.tar.gz.

# 传输后合并
cat opc200-offline.tar.gz.* > opc200-offline.tar.gz

# 方法2：只传配置，镜像本地准备
# 只复制.env和脚本
# 镜像在目标机器单独准备
```

### 问题3：目标机器Docker版本太旧

**现象**：加载镜像失败

**解决**：
```bash
# 离线安装Docker较复杂，建议：
# 1. 找一台同系统的联网机器，安装相同版本Docker
# 2. 将Docker二进制文件打包传输
# 3. 或使用系统ISO中的Docker包

# CentOS/RHEL
rpm -ivh docker-ce-*.rpm

# Ubuntu/Debian
dpkg -i docker-ce_*.deb
```

---

## 📊 方案对比

| 对比项 | 国内镜像源 | 离线部署 |
|-------|-----------|---------|
| 网络要求 | 需要（国内访问） | 完全不需要 |
| 包大小 | ~10KB（仅脚本） | ~2-3GB（含镜像） |
| 部署时间 | 10-20分钟（依赖网络） | 5-10分钟 |
| 适用场景 | 有网络但无梯子 | 完全无网络 |
| Docker要求 | 自动安装 | 需预装 |
| 维护难度 | 低 | 高（需定期更新镜像） |

---

## 💡 最佳实践

### 给客户的建议

1. **优先使用国内镜像源**：
   - 客户有网络但无梯子时最方便
   - 能保持镜像最新
   - 部署包体积小

2. **离线部署作为备选**：
   - 用于完全隔离的网络环境
   - 金融、政府等安全要求高的场景

3. **预装Docker**：
   - 在交付的机器镜像中预装Docker
   - 减少客户部署障碍

### 版本更新策略

**国内镜像源方案**：
- 自动获取最新镜像
- 只需更新脚本

**离线部署方案**：
- 需定期重新导出镜像包
- 建议每月或每季度更新

---

## 📞 求助

如仍无法解决：
1. 检查Docker版本：`docker version`
2. 检查网络：`ping docker.1panel.live`
3. 查看详细日志：`docker info`
4. 联系支持：提供错误日志和环境信息

---

**版本**: v1.0  
**更新**: 2026-04-07
