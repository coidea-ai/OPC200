# OPC200 5实例部署 - 快速开始指南

## 📋 部署流程

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. 复制模板    │ →  │  2. 填写配置    │ →  │  3. 验证配置    │
│                 │    │                 │    │                 │
│ cp .env.template│    │ vi .env         │    │ bash validate-  │
│    .env         │    │                 │    │    config.sh    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  4. 执行部署    │ →  │  5. 验证部署    │ →  │  6. 开始使用    │
│                 │    │                 │    │                 │
│ bash deploy-    │    │ python3         │    │ 访问各实例     │
│ from-env.sh     │    │ validate-5-     │    │ Dashboard      │
│                 │    │ instances.py    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🚀 快速部署（3步）

### 第1步：复制并填写配置

```bash
# 进入项目目录
cd /path/to/OPC200

# 复制配置模板
cp .env.template .env

# 编辑配置（必填项）
vi .env
```

**最少需要填写的内容**（约5行）：
```bash
# 中转站API Key（从 https://api.apiatlas.com 获取）
APIATLAS_API_KEY=sk-your-key-here

# 其他保持默认即可
```

### 第2步：验证配置

```bash
bash scripts/deploy/validate-config.sh

# 预期输出:
# [✓] [REQUIRED] APIATLAS_API_KEY: 已填写
# [✓] [REQUIRED] GATEWAY_TOKEN_PREFIX: 已填写
# ...
# ✓ 所有检查通过！配置有效。
```

### 第3步：一键部署

```bash
bash scripts/deploy/deploy-from-env.sh

# 预期输出:
# [STEP 0/7] 加载配置文件...
# [STEP 1/7] 验证配置...
# [STEP 2/7] 创建目录结构...
# ...
# 部署准备完成!
# 启动: sudo /opt/opc200/start-all.sh
```

---

## ⚙️ 配置文件详解

### 文件位置
```
OPC200/
├── .env.template          # 配置模板（参考用）
├── .env                   # ← 你的配置文件
└── scripts/deploy/
    ├── validate-config.sh # 验证脚本
    ├── deploy-from-env.sh # 部署脚本
    └── validate-5-instances.py  # 验证脚本
```

### 配置项分类

#### [REQUIRED] 必填项
```bash
# 中转站API配置
APIATLAS_API_KEY=sk-xxxxxxxxxx        # 从api.apiatlas.com获取

# 安全配置
GATEWAY_TOKEN_PREFIX=opc200-token     # Gateway Token前缀
GRAFANA_PASSWORD_PREFIX=admin         # Grafana密码前缀
```

#### [OPTIONAL] 常用选项
```bash
# 实例数量（默认: 5）
INSTANCE_COUNT=5
INSTANCE_IDS="opc-001 opc-002 opc-003 opc-004 opc-005"

# 部署目录（默认: /opt/opc200）
BASE_DIR=/opt/opc200

# 模型配置（默认: gemini-3-flash-preview）
DEFAULT_MODEL=gemini-3-flash-preview

# 功能开关
ENABLE_TAILSCALE=false       # Tailscale VPN
ENABLE_MONITORING=true       # Prometheus + Grafana
AUTO_START=false            # 自动启动
```

#### [OPTIONAL] 高级选项
```bash
# 端口配置（一般保持默认）
GATEWAY_BASE_PORT=18789
PROMETHEUS_BASE_PORT=9090
GRAFANA_BASE_PORT=3000

# 资源限制（可选）
GATEWAY_MEMORY_LIMIT=1g
JOURNAL_MEMORY_LIMIT=2g

# 数据保留
LOG_RETENTION_DAYS=30
BACKUP_RETENTION_DAYS=30
```

---

## 📊 配置示例

### 示例1：最小配置
```bash
# .env
APIATLAS_API_KEY=sk-your-key-here
GATEWAY_TOKEN_PREFIX=opc200-token
GRAFANA_PASSWORD_PREFIX=admin
```

### 示例2：完整配置
```bash
# .env
BASE_DIR=/opt/opc200
INSTANCE_COUNT=5
INSTANCE_IDS="opc-001 opc-002 opc-003 opc-004 opc-005"

APIATLAS_API_KEY=sk-your-key-here
APIATLAS_URL=https://api.apiatlas.com/v1
DEFAULT_MODEL=gemini-3-flash-preview

GATEWAY_TOKEN_PREFIX=opc200-token
GRAFANA_PASSWORD_PREFIX=admin

GATEWAY_BASE_PORT=18789
ENABLE_TAILSCALE=false
ENABLE_MONITORING=true
AUTO_START=false
```

### 示例3：3实例测试配置
```bash
# .env - 减少实例数量用于测试
INSTANCE_COUNT=3
INSTANCE_IDS="opc-001 opc-002 opc-003"

APIATLAS_API_KEY=sk-your-key-here
GATEWAY_TOKEN_PREFIX=opc200-token
GRAFANA_PASSWORD_PREFIX=admin
```

---

## 🔍 验证配置

### 验证脚本检查项

| 检查类别 | 检查内容 |
|---------|---------|
| **必填项** | API Key、Token前缀、密码前缀 |
| **端口** | 端口范围、是否被占用 |
| **实例** | ID数量匹配、格式正确 |
| **选填项** | 默认值提示 |
| **资源** | 内存、磁盘充足 |
| **Docker** | Docker和Compose已安装 |

### 验证结果

**✓ 通过**
```
✓ 所有检查通过！配置有效。

下一步:
  bash scripts/deploy/deploy-from-env.sh
```

**⚠ 警告（可继续）**
```
! 配置基本有效，但有 2 个警告

可以部署，但建议先处理警告:
  vi .env

或继续部署:
  bash scripts/deploy/deploy-from-env.sh
```

**✗ 失败（需修复）**
```
✗ 配置验证失败，有 3 个错误

请修改配置后重试:
  vi .env

然后重新验证:
  bash scripts/deploy/validate-config.sh
```

---

## 🎯 部署命令

### 标准部署（生成配置 + 手动启动）
```bash
bash scripts/deploy/deploy-from-env.sh

# 输出会提示:
# 手动启动:
#   sudo /opt/opc200/start-all.sh
```

### 自动启动部署
```bash
# 修改 .env
AUTO_START=true

# 重新部署
bash scripts/deploy/deploy-from-env.sh
# 会自动启动所有实例
```

### 从指定配置部署
```bash
bash scripts/deploy/deploy-from-env.sh /path/to/custom.env
```

---

## 🔧 常用管理命令

### 启动/停止
```bash
# 启动所有
sudo /opt/opc200/start-all.sh

# 停止所有
sudo /opt/opc200/stop-all.sh

# 查看状态
sudo /opt/opc200/status-all.sh
```

### 单个实例管理
```bash
# 启动单个
cd /opt/opc200/opc-001 && docker-compose up -d

# 停止单个
cd /opt/opc200/opc-001 && docker-compose down

# 查看日志
cd /opt/opc200/opc-001 && docker-compose logs -f gateway
```

### 测试验证
```bash
# 测试模型配置
sudo /opt/opc200/test-models.sh

# 完整验证
python3 scripts/deploy/validate-5-instances.py
```

---

## 🌐 访问地址

部署完成后，各服务地址：

| 实例 | Gateway | Prometheus | Grafana |
|------|---------|------------|---------|
| opc-001 | http://127.0.0.1:18789 | http://127.0.0.1:9090 | http://127.0.0.1:3000 |
| opc-002 | http://127.0.0.1:18790 | http://127.0.0.1:9091 | http://127.0.0.1:3001 |
| opc-003 | http://127.0.0.1:18791 | http://127.0.0.1:9092 | http://127.0.0.1:3002 |
| opc-004 | http://127.0.0.1:18792 | http://127.0.0.1:9093 | http://127.0.0.1:3003 |
| opc-005 | http://127.0.0.1:18793 | http://127.0.0.1:9094 | http://127.0.0.1:3004 |

---

## 🆘 故障排查

### 问题1：配置文件不存在
```bash
Error: 配置文件不存在: .env

解决:
  cp .env.template .env
  vi .env  # 填写配置
```

### 问题2：API Key无效
```bash
[✗] [REQUIRED] APIATLAS_API_KEY 未填写

解决:
  vi .env
  # 添加: APIATLAS_API_KEY=sk-your-key
```

### 问题3：端口被占用
```bash
[!] Gateway端口 (18789) 已被占用

解决:
  vi .env
  # 修改: GATEWAY_BASE_PORT=18800  # 换一个基础端口
```

### 问题4：内存不足
```bash
[!] 内存可能不足，建议至少 25GB

解决:
  vi .env
  # 减少实例数量:
  INSTANCE_COUNT=3
  INSTANCE_IDS="opc-001 opc-002 opc-003"
```

---

## 📝 完整流程示例

```bash
# 1. 进入目录
cd /path/to/OPC200

# 2. 复制模板
cp .env.template .env

# 3. 填写配置（只需填API Key）
cat > .env << 'EOF'
APIATLAS_API_KEY=sk-your-api-key-from-apiatlas
GATEWAY_TOKEN_PREFIX=opc200-token
GRAFANA_PASSWORD_PREFIX=admin
EOF

# 4. 验证配置
bash scripts/deploy/validate-config.sh

# 5. 执行部署
bash scripts/deploy/deploy-from-env.sh

# 6. 启动服务
sudo /opt/opc200/start-all.sh

# 7. 验证部署
python3 scripts/deploy/validate-5-instances.py

# 8. 测试模型
sudo /opt/opc200/test-models.sh
```

---

## 📚 相关文档

- [5实例部署方案](DEPLOYMENT_5_INSTANCES.md) - 详细技术方案
- [配置模板](../.env.template) - 完整配置选项
- [运维速查卡](5_INSTANCES_CHEATSHEET.md) - 日常管理命令

---

**版本**: v1.0  
**更新**: 2026-04-07
