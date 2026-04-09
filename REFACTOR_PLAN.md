# OPC200 重构执行计划

> **基于**: CRITICAL_ANALYSIS_2026-04-10.md  
> **启动日期**: 2026-04-10  
> **目标**: 从"大而全的 Journal 工具集"转身成为"One Person Company 的 100 天成长协议"

---

## 重构纲领

1. **不再和 OpenClaw 平台赛跑**
2. **把维护面砍半**
3. **让 200 客户目标在架构上成为可能**
4. **把陪伴式服务从产品口号变成运营现实**

---

## Phase 1: Skill 层止血 (Day 1-2)

### 1.1 废弃 `opc-remi-lite`
- [x] 添加 DEPRECATED 标记
- [x] 更新 README 说明废弃原因
- [x] 从 `skills/README.md` 中移除
- [x] 从安装脚本中移除

### 1.2 精简 `opc-journal-suite` 子技能
- [ ] `opc-async-task-manager` → **标记为 legacy**（OpenClaw Task Flow 已覆盖）
- [ ] `opc-pattern-recognition` → **重构为解读层**（从 dreams.md 读取，做 OPC 特定解读）
- [ ] `opc-journal-core` → **保留但精简**，保留 100 天旅程 API
- [ ] `opc-milestone-tracker` → **保留**，核心差异化
- [ ] `opc-insight-generator` → **保留**，数据源从自研分析切到 dreaming output + OPC 上下文

### 1.3 更新协调层
- [ ] 更新 `coordinate.py` 的路由逻辑
- [ ] 更新 `config.yml` 去除废弃技能的配置块
- [ ] 更新测试，移除废弃技能的测试用例

---

## Phase 2: 部署架构换骨 (Day 3-7)

### 2.1 云端：多租户 Shared Services
- [ ] 新建 `docker-compose.cloud.yml`
- [ ] 设计共享 Qdrant cluster（按 collection 隔离）
- [ ] 单 Gateway 实例带租户路由（或 Gateway-per-tenant 但共享 infra）
- [ ] 移除"每个客户 7 个容器"的设计

### 2.2 本地：All-in-One
- [ ] 新建 `Dockerfile.allinone`
- [ ] 合并 Gateway + Journal + SQLite 到 1-2 容器
- [ ] Qdrant 变为可选（小客户用 sqlite-vec 替代）
- [ ] 新建 `docker-compose.onprem.yml`

### 2.3 部署比例调整
- [ ] `SYSTEM.md`: 150:50 → **20:180**
- [ ] `DEPLOYMENT_CHECKLIST`: 更新机器规格和成本估算
- [ ] `README.md`: 更新定位和目标客户画像

---

## Phase 3: 运营层落地 (Day 8-14)

### 3.1 客户健康评分
- [ ] 扩展 `health-check.sh`
- [ ] 定义评分指标：Gateway 在线、最后心跳、磁盘、错误率
- [ ] 输出标准化 JSON 供 dashboard 消费

### 3.2 Support Dashboard
- [ ] 最小 Grafana 面板：红绿灯视图（红/黄/绿）
- [ ] 按客户编号聚合
- [ ] 告警规则：离线 > 5min → P0，磁盘 > 80% → P1

### 3.3 SLA 文档化
- [ ] 新建 `docs/SLA.md`
- [ ] P0/P1/P2 分级和响应时间

---

## 验收标准

- [ ] `opc-remi-lite` 明确废弃且不影响构建
- [ ] `opc-journal-suite` 子技能从 5 个压缩到 3 个有效技能
- [ ] 新的云端 compose 文件可以在一台 host 上跑多个租户
- [ ] 新的本地 all-in-one 镜像 ≤ 2 个服务
- [ ] `SYSTEM.md` 的目标比例更新为 20:180
- [ ] 有可以手动刷新的客户健康红绿灯面板

---

*开始执行时间: 2026-04-10 04:30+08:00*
