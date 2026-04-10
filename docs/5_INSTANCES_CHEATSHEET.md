# OPC200 5实例快速参考

## 🚀 快速开始（3步部署）

```bash
# 1. 生成配置
bash scripts/deploy/generate-5-instances.sh

# 2. 启动所有实例
sudo /opt/opc200/start-all.sh

# 3. 验证部署
python3 scripts/deploy/validate-5-instances.py
```

---

## 📊 常用命令

### 查看状态
```bash
# 查看所有实例状态
sudo /opt/opc200/status-all.sh

# Docker容器列表
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 资源使用
docker stats --no-stream

# 系统资源
free -h && df -h
```

### 管理实例
```bash
# 启动所有
sudo /opt/opc200/start-all.sh

# 停止所有
sudo /opt/opc200/stop-all.sh

# 启动单个实例
cd /opt/opc200/opc-001 && docker-compose up -d

# 停止单个实例
cd /opt/opc200/opc-001 && docker-compose down

# 重启单个实例
cd /opt/opc200/opc-001 && docker-compose restart
```

### 查看日志
```bash
# 查看所有Gateway日志
for i in {001..005}; do
  echo "=== opc-$i Gateway ==="
  docker logs opc-$i-gateway --tail 20
done

# 实时跟踪某个实例
cd /opt/opc200/opc-001 && docker-compose logs -f

# 查看特定服务
docker logs opc-001-gateway --tail 100
docker logs opc-001-journal --tail 100
docker logs opc-001-qdrant --tail 100
```

---

## 🔧 故障排查

### 检查容器状态
```bash
docker ps -a | grep opc-
docker-compose -f /opt/opc200/opc-001/docker-compose.yml ps
```

### 检查网络
```bash
# 查看Docker网络
docker network ls | grep opc-

# 检查端口占用
sudo ss -tlnp | grep -E '1878|909|3000|6333'
```

### 进入容器调试
```bash
# 进入Gateway容器
docker exec -it opc-001-gateway /bin/sh

# 进入Journal容器
docker exec -it opc-001-journal /bin/sh

# 测试内部网络
docker exec opc-001-gateway ping qdrant
```

---

## 🌐 服务访问地址

| 实例 | Gateway | Prometheus | Grafana | Qdrant |
|------|---------|------------|---------|--------|
| opc-001 | http://127.0.0.1:18789 | http://127.0.0.1:9090 | http://127.0.0.1:3000 | http://127.0.0.1:6333 |
| opc-002 | http://127.0.0.1:18790 | http://127.0.0.1:9091 | http://127.0.0.1:3001 | http://127.0.0.1:6334 |
| opc-003 | http://127.0.0.1:18791 | http://127.0.0.1:9092 | http://127.0.0.1:3002 | http://127.0.0.1:6335 |
| opc-004 | http://127.0.0.1:18792 | http://127.0.0.1:9093 | http://127.0.0.1:3003 | http://127.0.0.1:6336 |
| opc-005 | http://127.0.0.1:18793 | http://127.0.0.1:9094 | http://127.0.0.1:3004 | http://127.0.0.1:6337 |

---

## 🧪 测试命令

```bash
# 完整验证
python3 scripts/deploy/validate-5-instances.py

# 负载测试
python3 scripts/deploy/load-test-5-instances.py

# 手动健康检查
for port in 18789 18790 18791 18792 18793; do
  curl -s http://127.0.0.1:$port/health && echo " ✓ Gateway $port"
done
```

---

## 📝 配置文件位置

```
/opt/opc200/
├── opc-001/
│   ├── docker-compose.yml      # Compose配置
│   ├── .env                    # 环境变量
│   ├── config/prometheus.yml   # Prometheus配置
│   ├── data/                   # 数据目录
│   │   ├── gateway/
│   │   ├── journal/
│   │   └── qdrant/
│   └── logs/                   # 日志目录
├── opc-002/ ... opc-005/
├── start-all.sh
├── stop-all.sh
└── status-all.sh
```

---

## 🧹 清理操作

```bash
# 停止并删除所有容器
sudo /opt/opc200/stop-all.sh

# 删除所有数据（危险！）
sudo rm -rf /opt/opc200/opc-*/data/*
sudo rm -rf /opt/opc200/opc-*/logs/*

# 删除Docker卷
docker volume prune

# 删除网络
docker network prune

# 完全清理（重新部署）
sudo rm -rf /opt/opc200
```

---

## 📈 监控检查清单

- [ ] 25个容器Running
- [ ] 20个端口监听
- [ ] Grafana可访问
- [ ] Prometheus targets正常
- [ ] 内存使用<50GB
- [ ] 磁盘空间充足
- [ ] 无错误日志
- [ ] 响应时间<1s

---

**提示**: 将此文件保存为速查卡，方便日常运维使用。
