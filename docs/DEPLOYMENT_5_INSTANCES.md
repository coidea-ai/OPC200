# OPC200 5实例部署方案

> **版本**: v1.0  
> **适用**: 单台4090 96G机器部署5个独立OPC200实例  
> **生成时间**: 2026-04-07

---

## 📋 方案概述

### 目标
在单台4090 96G机器上部署**5个完全独立的OPC200实例**，验证：
1. 多实例部署的可行性
2. 端口隔离和资源分配
3. 数据隔离和独立性
4. 监控和运维流程

### 架构设计

```
4090 96G 机器
├── opc-001/          # 实例1: 端口 18789, 9090, 3000, 6333
│   ├── docker-compose.yml
│   ├── data/
│   ├── logs/
│   └── config/
├── opc-002/          # 实例2: 端口 18790, 9091, 3001, 6334
├── opc-003/          # 实例3: 端口 18791, 9092, 3002, 6335
├── opc-004/          # 实例4: 端口 18792, 9093, 3003, 6336
├── opc-005/          # 实例5: 端口 18793, 9094, 3004, 6337
├── start-all.sh      # 一键启动
├── stop-all.sh       # 一键停止
└── status-all.sh     # 状态检查
```

### 端口分配

| 实例 | Gateway | Prometheus | Grafana | Qdrant | Journal |
|------|---------|------------|---------|--------|---------|
| opc-001 | 18789 | 9090 | 3000 | 6333 | 8080 |
| opc-002 | 18790 | 9091 | 3001 | 6334 | 8081 |
| opc-003 | 18791 | 9092 | 3002 | 6335 | 8082 |
| opc-004 | 18792 | 9093 | 3003 | 6336 | 8083 |
| opc-005 | 18793 | 9094 | 3004 | 6337 | 8084 |

### 资源预估

| 资源 | 单实例 | 5实例总计 | 4090可用 | 使用率 |
|------|--------|-----------|----------|--------|
| RAM | ~4.2GB | ~21GB | 96GB | 22% |
| CPU | ~3 cores | ~15 cores | 32+ cores | 47% |
| 磁盘 | ~10GB | ~50GB | 充足 | - |

---

## 🔧 需要修改的文件

### 1. 新增文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `generate-5-instances.sh` | `scripts/deploy/` | 生成5实例配置 |
| `validate-5-instances.py` | `scripts/deploy/` | 验证测试脚本 |
| `docker-compose.yml` (x5) | `/opt/opc200/opc-00x/` | 各实例Compose配置 |
| `prometheus.yml` (x5) | `/opt/opc200/opc-00x/config/` | Prometheus配置 |
| `.env` (x5) | `/opt/opc200/opc-00x/` | 环境变量 |

### 2. 模板修改内容

**docker-compose.yml 关键修改：**
```yaml
# 1. 端口递增
ports:
  - "127.0.0.1:${GATEWAY_PORT}:${GATEWAY_PORT}"
  
# 2. 容器名称加前缀
container_name: ${INSTANCE_ID}-gateway

# 3. 独立网络(避免冲突)
networks:
  ${INSTANCE_ID}-network:
    ipam:
      config:
        - subnet: 172.20.x.0/16  # 每个实例不同网段

# 4. Tailscale 注释掉
# tailscale:
#   ...
```

**主要修改点：**
1. ✅ 端口偏移：每个实例使用不同的端口范围
2. ✅ 网络隔离：每个实例独立的Docker网络
3. ✅ 命名隔离：容器名加实例前缀
4. ✅ 数据隔离：各实例独立的data目录
5. ✅ Tailscale禁用：单机器测试不需要VPN

---

## 🧪 测试计划

### 测试层级

```
Level 1: 部署测试 (必做)
├── 环境检查
├── 容器启动
└── 端口监听

Level 2: 功能测试 (必做)
├── 健康检查
├── 服务互通
├── Prometheus指标
└── Grafana访问

Level 3: 隔离测试 (必做)
├── 数据隔离
├── 网络隔离
└── 资源隔离

Level 4: 压力测试 (可选)
├── 并发访问
├── 资源峰值
└── 稳定性(24h)
```

### 详细测试用例

#### 测试1: 环境检查
- **目的**: 确认系统环境满足要求
- **步骤**:
  1. 检查Docker运行状态
  2. 检查Docker Compose版本
  3. 检查目录权限
  4. 检查磁盘空间
- **通过标准**: 所有检查项通过

#### 测试2: 容器运行状态
- **目的**: 确认25个容器(5实例×5服务)全部运行
- **步骤**:
  1. 执行 `docker ps`
  2. 检查容器数量
  3. 检查容器状态(Up/Healthy)
- **通过标准**: 25个容器全部Running

#### 测试3: 端口监听检查
- **目的**: 确认20个端口(5实例×4端口)正常监听
- **步骤**:
  1. 使用 `ss -tln` 检查端口
  2. 验证每个实例的4个端口
- **通过标准**: 所有端口处于LISTEN状态

#### 测试4: 健康检查
- **目的**: 确认所有服务健康
- **步骤**:
  1. `docker-compose ps` 查看状态
  2. 检查Health列
- **通过标准**: 所有容器状态为healthy

#### 测试5: 数据隔离验证
- **目的**: 确认5实例数据完全隔离
- **步骤**:
  1. 向opc-001写入测试数据
  2. 检查opc-002~005是否可见
  3. 反向测试
- **通过标准**: 数据不跨实例泄露

#### 测试6: 资源使用检查
- **目的**: 确认资源占用在预期范围内
- **步骤**:
  1. `docker stats` 查看容器资源
  2. `free -h` 查看内存
  3. `df -h` 查看磁盘
- **通过标准**: 总内存<50GB，磁盘充足

#### 测试7: 服务互通验证
- **目的**: 确认每个实例内部服务互通
- **步骤**:
  1. Gateway → Qdrant 连通性测试
  2. Journal → Qdrant 连通性测试
- **通过标准**: 内部网络互通正常

#### 测试8: Prometheus指标
- **目的**: 确认监控正常工作
- **步骤**:
  1. 访问 `http://localhost:9090/api/v1/status/targets`
  2. 检查target状态
- **通过标准**: 所有target为UP状态

#### 测试9: Grafana访问
- **目的**: 确认可视化正常
- **步骤**:
  1. 访问 `http://localhost:3000/api/health`
  2. 检查返回状态码
- **通过标准**: 返回HTTP 200

---

## 🚀 实施步骤

### 准备阶段 (10分钟)

```bash
# 1. 登录4090机器
ssh user@4090-server

# 2. 确认Docker安装
docker --version
docker-compose --version

# 3. 创建基础目录
sudo mkdir -p /opt/opc200
sudo chown $USER:$USER /opt/opc200
```

### 部署阶段 (15分钟)

```bash
# 1. 进入项目目录
cd /path/to/OPC200

# 2. 运行生成脚本
bash scripts/deploy/generate-5-instances.sh

# 3. 检查生成的配置
ls -la /opt/opc200/
cat /opt/opc200/opc-001/docker-compose.yml

# 4. 启动所有实例
sudo /opt/opc200/start-all.sh
```

### 验证阶段 (5分钟)

```bash
# 1. 查看状态
sudo /opt/opc200/status-all.sh

# 2. 运行完整验证
python3 scripts/deploy/validate-5-instances.py

# 3. 查看报告
cat /opt/opc200/validation-report.json
```

---

## 📁 生成的文件清单

执行 `generate-5-instances.sh` 后会生成：

```
/opt/opc200/
├── opc-001/
│   ├── docker-compose.yml      # 实例1Compose配置
│   ├── .env                    # 环境变量
│   ├── config/
│   │   └── prometheus.yml      # Prometheus配置
│   ├── data/                   # 数据目录(运行时创建)
│   │   ├── gateway/
│   │   ├── journal/
│   │   └── qdrant/
│   └── logs/                   # 日志目录(运行时创建)
├── opc-002/
│   └── ... (同上结构)
├── opc-003/
├── opc-004/
├── opc-005/
├── start-all.sh                # 启动脚本
├── stop-all.sh                 # 停止脚本
└── status-all.sh               # 状态检查脚本
```

---

## 🔍 常见问题排查

### Q1: 端口冲突
**现象**: `bind: address already in use`
**解决**: 
```bash
# 检查占用端口的进程
sudo ss -tlnp | grep 18789
# 杀死冲突进程或更换端口
```

### Q2: 容器启动失败
**现象**: `Container exited with code 1`
**解决**:
```bash
# 查看日志
cd /opt/opc200/opc-001
docker-compose logs gateway
# 检查配置
docker-compose config
```

### Q3: 内存不足
**现象**: `OOM Killed` 或系统卡顿
**解决**:
```bash
# 减少同时运行的实例数
sudo /opt/opc200/stop-all.sh
# 只启动2-3个实例测试
```

### Q4: 网络冲突
**现象**: `Network overlaps with existing network`
**解决**:
```bash
# 清理旧网络
docker network prune
# 重新生成配置
```

---

## 📊 成功标准

验证通过的标准：

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| 容器数量 | 25个Running | `docker ps \| wc -l` |
| 端口监听 | 20个端口LISTEN | `ss -tln` |
| 健康状态 | 全部healthy | `docker-compose ps` |
| 数据隔离 | 无跨实例泄露 | 验证脚本 |
| 内存使用 | <50GB | `free -h` |
| 测试通过率 | 9/9通过 | 验证脚本 |

---

## 📞 后续步骤

验证成功后：

1. **性能测试**: 使用负载生成器测试并发
2. **稳定性测试**: 运行24-48小时观察
3. **扩展测试**: 尝试部署10-20个实例
4. **文档更新**: 记录实际资源使用情况
5. **生产准备**: 制定批量部署SOP

---

## ⚠️ 注意事项

1. **不要在生产环境直接运行**: 此方案用于测试验证
2. **备份重要数据**: 测试前确认无重要数据在/opt/opc200
3. **监控资源**: 4090机器可能被其他任务占用资源
4. **及时清理**: 测试完成后及时停止容器释放资源

---

**生成时间**: 2026-04-07  
**维护者**: OPC200 DevOps Team
