# OPC200 7×24 大规模仿真测试架构

> 150本地 + 50云端 OpenClaw 实例全天候压力测试与自动优化系统

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     仿真测试控制中心                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ 场景编排器   │  │ 负载生成器   │  │ 数据分析与优化引擎       │ │
│  │ Scenario    │  │ Load Gen    │  │ Analysis & Improvement  │ │
│  │ Orchestrator│  │             │  │ Engine                  │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼────────────────────┼────────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        实例集群层                                │
│  ┌────────────────────────┐    ┌────────────────────────────┐  │
│  │   本地实例池 (150个)    │    │     云端实例池 (50个)        │  │
│  │  ┌────┐ ┌────┐ ┌────┐  │    │  ┌────┐ ┌────┐ ┌────┐      │  │
│  │  │L1  │ │L2  │ │... │  │    │  │C1  │ │C2  │ │... │      │  │
│  │  │OPC │ │OPC │ │L150│  │    │  │OPC │ │OPC │ │C50 │      │  │
│  │  └────┘ └────┘ └────┘  │    │  └────┘ └────┘ └────┘      │  │
│  │  Docker Compose / K3s  │    │  Kubernetes / ECS           │  │
│  └────────────────────────┘    └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        观测层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Prometheus  │  │   Grafana   │  │      ELK Stack          │ │
│  │ 指标收集     │  │  可视化     │  │    日志分析              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 部署架构

### 2.1 本地实例池 (150个)

使用 Docker Compose + 容器编排:

```yaml
# docker-compose.simulation.yml
version: '3.8'

services:
  # OpenClaw Gateway (共享)
  gateway:
    image: ghcr.io/openclaw/openclaw:latest
    ports:
      - "8080:8080"
    environment:
      - SIMULATION_MODE=true
      - MAX_AGENTS=200
    volumes:
      - ./config/gateway.simulation.yml:/etc/openclaw/gateway.yml
    networks:
      - opc-simulation

  # 本地 Agent 实例 (批量生成)
  agent-local:
    image: openclaw/agent:2026.3
    deploy:
      replicas: 150
    environment:
      - AGENT_MODE=local
      - GATEWAY_URL=http://gateway:8080
      - SIMULATION_CUSTOMER_ID=SIM-${HOSTNAME}
      - LOG_LEVEL=info
    volumes:
      - agent-data:/data
    depends_on:
      - gateway
    networks:
      - opc-simulation
    # 资源限制模拟真实环境
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  # 技能套件 (每个实例独立)
  skills-suite:
    image: openclaw/skills:opc-journal-2.3.0
    deploy:
      replicas: 150
    volumes:
      - ./skills:/opt/openclaw/skills:ro
      - skills-data:/data/skills
    networks:
      - opc-simulation

  # 观测代理
  observability-agent:
    image: prometheus/node-exporter:latest
    networks:
      - opc-simulation

volumes:
  agent-data:
  skills-data:

networks:
  opc-simulation:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 2.2 云端实例池 (50个)

使用 Kubernetes + HPA:

```yaml
# k8s/cloud-agents.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opc-cloud-agents
  namespace: opc-simulation
spec:
  replicas: 50
  selector:
    matchLabels:
      app: opc-cloud-agent
  template:
    metadata:
      labels:
        app: opc-cloud-agent
        simulation: "true"
    spec:
      containers:
      - name: agent
        image: openclaw/agent:2026.3
        env:
        - name: AGENT_MODE
          value: "cloud"
        - name: SIMULATION_CUSTOMER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: opc-cloud-agents-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: opc-cloud-agents
  minReplicas: 50
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 3. 负载生成器

### 3.1 负载配置

```python
# simulation/load_generator.py
"""负载生成器 - 模拟真实用户行为."""

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict
import aiohttp


class UserType(Enum):
    """用户类型."""
    LIGHT = "light"      # 轻度用户: 每天1-2次交互
    REGULAR = "regular"  # 普通用户: 每天5-10次交互
    POWER = "power"      # 重度用户: 每天20+次交互
    BUSINESS = "business" # 商业用户: 持续高频交互


@dataclass
class LoadPattern:
    """负载模式."""
    user_type: UserType
    daily_interactions: tuple  # (min, max)
    peak_hours: List[int]      # 高峰时段
    skill_usage: Dict[str, float]  # 技能使用概率


# 预定义负载模式
PATTERNS = {
    UserType.LIGHT: LoadPattern(
        user_type=UserType.LIGHT,
        daily_interactions=(1, 3),
        peak_hours=[9, 12, 20],
        skill_usage={
            "journal_record": 0.6,
            "journal_search": 0.3,
            "daily_summary": 0.1
        }
    ),
    UserType.REGULAR: LoadPattern(
        user_type=UserType.REGULAR,
        daily_interactions=(5, 12),
        peak_hours=[9, 12, 14, 20, 22],
        skill_usage={
            "journal_record": 0.4,
            "pattern_analyze": 0.2,
            "milestone_detect": 0.15,
            "task_create": 0.15,
            "insight_generate": 0.1
        }
    ),
    UserType.POWER: LoadPattern(
        user_type=UserType.POWER,
        daily_interactions=(15, 30),
        peak_hours=list(range(8, 24)),
        skill_usage={
            "journal_record": 0.25,
            "pattern_analyze": 0.2,
            "milestone_detect": 0.15,
            "task_create": 0.2,
            "insight_generate": 0.15,
            "journal_search": 0.05
        }
    ),
    UserType.BUSINESS: LoadPattern(
        user_type=UserType.BUSINESS,
        daily_interactions=(50, 100),
        peak_hours=list(range(0, 24)),  # 全天候
        skill_usage={
            "journal_record": 0.3,
            "task_create": 0.3,
            "pattern_analyze": 0.2,
            "cron_schedule": 0.2
        }
    )
}


class LoadGenerator:
    """负载生成器."""
    
    def __init__(self, agent_pool: List[str]):
        self.agent_pool = agent_pool
        self.active_sessions: Dict[str, LoadPattern] = {}
        
    def assign_user_types(self):
        """为每个实例分配用户类型."""
        weights = [0.4, 0.35, 0.15, 0.1]  # light, regular, power, business
        user_types = random.choices(
            list(UserType), 
            weights=weights, 
            k=len(self.agent_pool)
        )
        
        for agent_id, user_type in zip(self.agent_pool, user_types):
            self.active_sessions[agent_id] = PATTERNS[user_type]
    
    async def generate_load(self, duration_hours: int = 24):
        """生成负载."""
        end_time = asyncio.get_event_loop().time() + (duration_hours * 3600)
        
        while asyncio.get_event_loop().time() < end_time:
            tasks = []
            current_hour = datetime.now().hour
            
            for agent_id, pattern in self.active_sessions.items():
                # 根据时段调整频率
                multiplier = 2.0 if current_hour in pattern.peak_hours else 0.5
                
                # 计算本次循环应产生的交互数
                base_interactions = random.randint(*pattern.daily_interactions)
                interactions = int(base_interactions * multiplier / 24)
                
                for _ in range(interactions):
                    task = self._send_interaction(agent_id, pattern)
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 每分钟一个周期
            await asyncio.sleep(60)
    
    async def _send_interaction(self, agent_id: str, pattern: LoadPattern):
        """发送单个交互."""
        # 选择技能
        skill = random.choices(
            list(pattern.skill_usage.keys()),
            weights=list(pattern.skill_usage.values())
        )[0]
        
        # 构建请求
        payload = self._build_payload(skill, agent_id)
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"http://{agent_id}:8080/skill",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return await resp.json()
            except Exception as e:
                # 记录失败用于后续分析
                await self._record_failure(agent_id, skill, str(e))
    
    def _build_payload(self, skill: str, agent_id: str) -> dict:
        """构建请求负载."""
        payloads = {
            "journal_record": {
                "intent": "journal_record",
                "content": f"Simulation entry from {agent_id}",
                "tags": ["simulation", "test"]
            },
            "pattern_analyze": {
                "intent": "pattern_analyze",
                "period": "7d"
            },
            "milestone_detect": {
                "intent": "milestone_detect",
                "threshold": 0.8
            },
            "task_create": {
                "intent": "task_create",
                "title": f"Simulated task from {agent_id}",
                "priority": random.choice(["low", "medium", "high"])
            },
            "insight_generate": {
                "intent": "insight_generate",
                "type": "daily_summary"
            }
        }
        return payloads.get(skill, {"intent": skill})
    
    async def _record_failure(self, agent_id: str, skill: str, error: str):
        """记录失败."""
        # 发送到监控中心
        pass
```

### 3.2 混沌测试

```python
# simulation/chaos_engine.py
"""混沌工程 - 模拟故障场景."""

import random
import asyncio
from enum import Enum


class FailureType(Enum):
    """故障类型."""
    NETWORK_LATENCY = "network_latency"      # 网络延迟
    NETWORK_PARTITION = "network_partition"  # 网络分区
    CPU_SPIKE = "cpu_spike"                  # CPU飙升
    MEMORY_PRESSURE = "memory_pressure"      # 内存压力
    DISK_FULL = "disk_full"                  # 磁盘满
    SERVICE_RESTART = "service_restart"      # 服务重启
    SKILL_CRASH = "skill_crash"              # 技能崩溃


class ChaosEngine:
    """混沌引擎."""
    
    def __init__(self, agent_pool: List[str]):
        self.agent_pool = agent_pool
        self.active_failures: Dict[str, FailureType] = {}
        
    async def run_chaos(self, duration_hours: int = 24):
        """运行混沌测试."""
        failure_scenarios = [
            (FailureType.NETWORK_LATENCY, 0.3),
            (FailureType.CPU_SPIKE, 0.2),
            (FailureType.MEMORY_PRESSURE, 0.2),
            (FailureType.SERVICE_RESTART, 0.15),
            (FailureType.SKILL_CRASH, 0.1),
            (FailureType.NETWORK_PARTITION, 0.05)
        ]
        
        end_time = asyncio.get_event_loop().time() + (duration_hours * 3600)
        
        while asyncio.get_event_loop().time() < end_time:
            # 每30分钟注入一次故障
            await asyncio.sleep(1800)
            
            # 随机选择5-10%的实例注入故障
            affected_count = max(1, int(len(self.agent_pool) * random.uniform(0.05, 0.1)))
            affected_agents = random.sample(self.agent_pool, affected_count)
            
            for agent in affected_agents:
                failure_type = random.choices(
                    [f[0] for f in failure_scenarios],
                    weights=[f[1] for f in failure_scenarios]
                )[0]
                
                await self._inject_failure(agent, failure_type)
                
            # 记录故障用于分析
            await self._record_chaos_event(affected_agents, failure_type)
    
    async def _inject_failure(self, agent_id: str, failure: FailureType):
        """注入故障."""
        injectors = {
            FailureType.NETWORK_LATENCY: self._inject_latency,
            FailureType.CPU_SPIKE: self._inject_cpu_spike,
            FailureType.MEMORY_PRESSURE: self._inject_memory_pressure,
            FailureType.SERVICE_RESTART: self._inject_restart,
            FailureType.SKILL_CRASH: self._inject_skill_crash,
            FailureType.NETWORK_PARTITION: self._inject_partition
        }
        
        injector = injectors.get(failure)
        if injector:
            await injector(agent_id)
    
    async def _inject_latency(self, agent_id: str):
        """注入网络延迟."""
        # 使用tc命令添加延迟
        pass
    
    async def _inject_cpu_spike(self, agent_id: str):
        """注入CPU飙升."""
        # 启动CPU密集型进程
        pass
    
    async def _inject_memory_pressure(self, agent_id: str):
        """注入内存压力."""
        # 分配大量内存
        pass
    
    async def _inject_restart(self, agent_id: str):
        """注入服务重启."""
        # 重启容器/服务
        pass
    
    async def _inject_skill_crash(self, agent_id: str):
        """注入技能崩溃."""
        # 杀死技能进程
        pass
    
    async def _inject_partition(self, agent_id: str):
        """注入网络分区."""
        # 隔离网络
        pass
```

---

## 4. 观测与数据收集

### 4.1 指标定义

```yaml
# simulation/metrics.yml
metrics:
  # 系统指标
  system:
    - name: opc_agent_cpu_usage
      type: gauge
      help: "Agent CPU使用率"
      labels: [agent_id, mode]
      
    - name: opc_agent_memory_usage_bytes
      type: gauge
      help: "Agent内存使用量"
      labels: [agent_id, mode]
      
    - name: opc_agent_disk_io_rate
      type: counter
      help: "磁盘IO速率"
      labels: [agent_id, operation]
      
  # 业务指标
  business:
    - name: opc_skill_invocations_total
      type: counter
      help: "技能调用总数"
      labels: [skill_name, agent_id, status]
      
    - name: opc_skill_duration_seconds
      type: histogram
      help: "技能执行耗时"
      labels: [skill_name]
      buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
      
    - name: opc_journal_entries_total
      type: counter
      help: "日志条目总数"
      labels: [agent_id, entry_type]
      
    - name: opc_insights_generated_total
      type: counter
      help: "洞察生成总数"
      labels: [agent_id, insight_type]
      
  # 质量指标
  quality:
    - name: opc_error_rate
      type: gauge
      help: "错误率"
      labels: [agent_id, error_type]
      
    - name: opc_recovery_time_seconds
      type: histogram
      help: "故障恢复时间"
      labels: [failure_type]
      
    - name: opc_data_consistency_score
      type: gauge
      help: "数据一致性评分"
      labels: [agent_id]
```

### 4.2 数据收集器

```python
# simulation/metrics_collector.py
"""指标收集器."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import asyncio
import aiohttp
from datetime import datetime


class MetricsCollector:
    """指标收集器."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # 定义指标
        self.skill_invocations = Counter(
            'opc_skill_invocations_total',
            'Total skill invocations',
            ['skill_name', 'agent_id', 'status'],
            registry=self.registry
        )
        
        self.skill_duration = Histogram(
            'opc_skill_duration_seconds',
            'Skill execution duration',
            ['skill_name'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.agent_health = Gauge(
            'opc_agent_health',
            'Agent health status (1=healthy, 0=unhealthy)',
            ['agent_id', 'mode'],
            registry=self.registry
        )
        
        self.error_rate = Gauge(
            'opc_error_rate',
            'Error rate percentage',
            ['agent_id', 'error_type'],
            registry=self.registry
        )
    
    async def collect_from_agents(self, agent_pool: List[str]):
        """从所有Agent收集指标."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._collect_agent_metrics(session, agent_id)
                for agent_id in agent_pool
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _collect_agent_metrics(self, session: aiohttp.ClientSession, agent_id: str):
        """收集单个Agent指标."""
        try:
            async with session.get(
                f"http://{agent_id}:8080/metrics",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                data = await resp.json()
                
                # 更新指标
                self.agent_health.labels(
                    agent_id=agent_id,
                    mode=data.get('mode', 'unknown')
                ).set(1 if data.get('healthy') else 0)
                
                # 记录技能调用统计
                for skill, count in data.get('skill_stats', {}).items():
                    self.skill_invocations.labels(
                        skill_name=skill,
                        agent_id=agent_id,
                        status='success'
                    ).inc(count)
                    
        except Exception as e:
            # Agent不可达，标记为不健康
            self.agent_health.labels(agent_id=agent_id, mode='unknown').set(0)
    
    def export_to_prometheus(self) -> str:
        """导出Prometheus格式."""
        from prometheus_client import generate_latest
        return generate_latest(self.registry).decode('utf-8')
```

---

## 5. 自动优化引擎

### 5.1 分析引擎

```python
# simulation/improvement_engine.py
"""自动优化引擎."""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PerformanceIssue:
    """性能问题."""
    issue_type: str
    severity: str  # critical, high, medium, low
    affected_agents: List[str]
    description: str
    recommendation: str
    confidence: float


@dataclass
class Optimization:
    """优化建议."""
    category: str
    action: str
    target: str
    expected_improvement: str
    implementation_difficulty: str
    priority: int


class ImprovementEngine:
    """改进引擎."""
    
    def __init__(self):
        self.issue_patterns = {
            'high_latency': {
                'threshold': 5.0,  # 5秒
                'metric': 'opc_skill_duration_seconds',
                'severity': 'high'
            },
            'high_error_rate': {
                'threshold': 0.05,  # 5%
                'metric': 'opc_error_rate',
                'severity': 'critical'
            },
            'memory_leak': {
                'threshold': 0.8,  # 80%内存使用率持续增长
                'metric': 'opc_agent_memory_usage_bytes',
                'severity': 'high'
            },
            'cpu_throttling': {
                'threshold': 0.9,  # 90% CPU
                'metric': 'opc_agent_cpu_usage',
                'severity': 'medium'
            },
            'skill_inefficiency': {
                'threshold': 10.0,  # 10秒以上
                'metric': 'opc_skill_duration_seconds_p99',
                'severity': 'medium'
            }
        }
    
    def analyze_performance(self, metrics_data: pd.DataFrame) -> List[PerformanceIssue]:
        """分析性能数据."""
        issues = []
        
        # 1. 检测高延迟
        latency_issues = self._detect_high_latency(metrics_data)
        issues.extend(latency_issues)
        
        # 2. 检测高错误率
        error_issues = self._detect_high_error_rate(metrics_data)
        issues.extend(error_issues)
        
        # 3. 检测内存泄漏
        memory_issues = self._detect_memory_leaks(metrics_data)
        issues.extend(memory_issues)
        
        # 4. 检测CPU瓶颈
        cpu_issues = self._detect_cpu_bottlenecks(metrics_data)
        issues.extend(cpu_issues)
        
        # 5. 检测低效技能
        skill_issues = self._detect_inefficient_skills(metrics_data)
        issues.extend(skill_issues)
        
        return sorted(issues, key=lambda x: self._severity_weight(x.severity), reverse=True)
    
    def _detect_high_latency(self, data: pd.DataFrame) -> List[PerformanceIssue]:
        """检测高延迟问题."""
        issues = []
        
        # 按技能分组计算P99延迟
        skill_latency = data.groupby('skill_name')['duration'].quantile(0.99)
        
        for skill, latency in skill_latency.items():
            if latency > self.issue_patterns['high_latency']['threshold']:
                affected = data[data['skill_name'] == skill]['agent_id'].unique().tolist()
                issues.append(PerformanceIssue(
                    issue_type='high_latency',
                    severity='high',
                    affected_agents=affected[:10],  # 限制数量
                    description=f"技能 {skill} P99延迟 {latency:.2f}s 超过阈值",
                    recommendation=f"考虑优化 {skill} 的实现或增加资源",
                    confidence=0.85
                ))
        
        return issues
    
    def _detect_high_error_rate(self, data: pd.DataFrame) -> List[PerformanceIssue]:
        """检测高错误率."""
        issues = []
        
        # 计算每个Agent的错误率
        error_rates = data.groupby('agent_id').apply(
            lambda x: (x['status'] == 'error').sum() / len(x)
        )
        
        high_error_agents = error_rates[error_rates > self.issue_patterns['high_error_rate']['threshold']]
        
        if len(high_error_agents) > 0:
            issues.append(PerformanceIssue(
                issue_type='high_error_rate',
                severity='critical',
                affected_agents=high_error_agents.index.tolist(),
                description=f"{len(high_error_agents)} 个Agent错误率超过5%",
                recommendation="检查日志分析根本原因，可能需要修复代码或增加重试机制",
                confidence=0.9
            ))
        
        return issues
    
    def _detect_memory_leaks(self, data: pd.DataFrame) -> List[PerformanceIssue]:
        """检测内存泄漏."""
        issues = []
        
        # 检测内存使用持续增长的趋势
        for agent_id in data['agent_id'].unique():
            agent_data = data[data['agent_id'] == agent_id].sort_values('timestamp')
            if len(agent_data) < 10:
                continue
                
            memory_trend = np.polyfit(
                range(len(agent_data)),
                agent_data['memory_usage'],
                1
            )[0]
            
            # 如果内存持续增长且当前使用率超过80%
            current_memory = agent_data['memory_usage'].iloc[-1]
            max_memory = agent_data['memory_limit'].iloc[-1]
            
            if memory_trend > 0 and current_memory / max_memory > 0.8:
                issues.append(PerformanceIssue(
                    issue_type='memory_leak',
                    severity='high',
                    affected_agents=[agent_id],
                    description=f"Agent {agent_id} 疑似内存泄漏，当前使用率 {(current_memory/max_memory)*100:.1f}%",
                    recommendation="检查是否有未释放的资源，考虑添加内存监控和自动重启机制",
                    confidence=0.75
                ))
        
        return issues
    
    def _detect_cpu_bottlenecks(self, data: pd.DataFrame) -> List[PerformanceIssue]:
        """检测CPU瓶颈."""
        issues = []
        
        high_cpu = data.groupby('agent_id')['cpu_usage'].mean()
        high_cpu_agents = high_cpu[high_cpu > self.issue_patterns['cpu_throttling']['threshold']]
        
        if len(high_cpu_agents) > 0:
            issues.append(PerformanceIssue(
                issue_type='cpu_throttling',
                severity='medium',
                affected_agents=high_cpu_agents.index.tolist()[:20],
                description=f"{len(high_cpu_agents)} 个Agent平均CPU使用率超过90%",
                recommendation="考虑优化算法复杂度或增加CPU配额",
                confidence=0.8
            ))
        
        return issues
    
    def _detect_inefficient_skills(self, data: pd.DataFrame) -> List[PerformanceIssue]:
        """检测低效技能."""
        issues = []
        
        # 找出执行时间最长的技能
        slow_skills = data.groupby('skill_name').agg({
            'duration': ['mean', 'max', 'count']
        }).reset_index()
        
        slow_skills.columns = ['skill_name', 'mean_duration', 'max_duration', 'count']
        slow_skills = slow_skills[slow_skills['mean_duration'] > 5.0]
        
        for _, row in slow_skills.iterrows():
            if row['count'] > 100:  # 只有使用频率高的才优化
                issues.append(PerformanceIssue(
                    issue_type='skill_inefficiency',
                    severity='medium',
                    affected_agents=[],
                    description=f"技能 {row['skill_name']} 平均执行时间 {row['mean_duration']:.2f}s (最大 {row['max_duration']:.2f}s)",
                    recommendation=f"优化 {row['skill_name']} 的实现，考虑使用缓存或异步处理",
                    confidence=0.7
                ))
        
        return issues
    
    def generate_optimizations(self, issues: List[PerformanceIssue]) -> List[Optimization]:
        """根据问题生成优化建议."""
        optimizations = []
        
        for issue in issues:
            if issue.issue_type == 'high_latency':
                optimizations.append(Optimization(
                    category='performance',
                    action='implement_caching',
                    target=issue.affected_agents,
                    expected_improvement='减少50%响应时间',
                    implementation_difficulty='medium',
                    priority=1
                ))
            
            elif issue.issue_type == 'high_error_rate':
                optimizations.append(Optimization(
                    category='reliability',
                    action='add_circuit_breaker',
                    target=issue.affected_agents,
                    expected_improvement='错误率降至1%以下',
                    implementation_difficulty='low',
                    priority=1
                ))
            
            elif issue.issue_type == 'memory_leak':
                optimizations.append(Optimization(
                    category='stability',
                    action='fix_memory_leak',
                    target=issue.affected_agents,
                    expected_improvement='消除内存泄漏',
                    implementation_difficulty='high',
                    priority=2
                ))
            
            elif issue.issue_type == 'cpu_throttling':
                optimizations.append(Optimization(
                    category='performance',
                    action='optimize_algorithm',
                    target=issue.affected_agents,
                    expected_improvement='CPU使用率降低30%',
                    implementation_difficulty='high',
                    priority=3
                ))
        
        return sorted(optimizations, key=lambda x: x.priority)
    
    def _severity_weight(self, severity: str) -> int:
        """严重级别权重."""
        weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        return weights.get(severity, 0)
```

### 5.2 自动优化执行器

```python
# simulation/auto_optimizer.py
"""自动优化执行器."""

import asyncio
import json
from typing import List
from datetime import datetime


class AutoOptimizer:
    """自动优化器."""
    
    def __init__(self, improvement_engine: ImprovementEngine):
        self.engine = improvement_engine
        self.optimization_history: List[dict] = []
        self.applied_optimizations: set = set()
    
    async def run_optimization_loop(self, interval_minutes: int = 60):
        """运行优化循环."""
        while True:
            print(f"[{datetime.now()}] 开始性能分析和优化...")
            
            # 1. 收集指标数据
            metrics_data = await self._collect_metrics()
            
            # 2. 分析问题
            issues = self.engine.analyze_performance(metrics_data)
            
            if issues:
                print(f"发现 {len(issues)} 个性能问题:")
                for issue in issues[:5]:  # 只显示前5个
                    print(f"  - [{issue.severity}] {issue.description}")
            
            # 3. 生成优化建议
            optimizations = self.engine.generate_optimizations(issues)
            
            # 4. 应用自动优化
            for opt in optimizations:
                if self._can_auto_apply(opt):
                    await self._apply_optimization(opt)
                else:
                    await self._create_ticket(opt)
            
            # 5. 生成报告
            await self._generate_report(issues, optimizations)
            
            print(f"[{datetime.now()}] 优化循环完成，等待 {interval_minutes} 分钟...")
            await asyncio.sleep(interval_minutes * 60)
    
    def _can_auto_apply(self, optimization: Optimization) -> bool:
        """判断是否可以自动应用优化."""
        # 低风险优化可以自动应用
        auto_apply_categories = {
            'add_circuit_breaker': True,
            'increase_timeout': True,
            'adjust_resource_limits': True,
            'enable_compression': True
        }
        
        return auto_apply_categories.get(optimization.action, False)
    
    async def _apply_optimization(self, optimization: Optimization):
        """应用优化."""
        print(f"应用优化: {optimization.action}")
        
        # 记录应用历史
        self.optimization_history.append({
            'timestamp': datetime.now().isoformat(),
            'optimization': optimization,
            'status': 'applied'
        })
        
        # 这里实现具体的优化逻辑
        # 例如：调整配置、重启服务等
        
    async def _create_ticket(self, optimization: Optimization):
        """创建工单（需要人工处理的优化）."""
        ticket = {
            'id': f"OPT-{datetime.now().strftime('%Y%m%d')}-{len(self.optimization_history)}",
            'category': optimization.category,
            'action': optimization.action,
            'difficulty': optimization.implementation_difficulty,
            'priority': optimization.priority,
            'created_at': datetime.now().isoformat()
        }
        
        print(f"创建优化工单: {ticket['id']}")
        # 可以集成到GitHub Issues或Jira
        
    async def _collect_metrics(self) -> pd.DataFrame:
        """收集指标数据."""
        # 从Prometheus或其他存储查询数据
        pass
    
    async def _generate_report(self, issues: List[PerformanceIssue], optimizations: List[Optimization]):
        """生成优化报告."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_issues': len(issues),
                'critical_issues': len([i for i in issues if i.severity == 'critical']),
                'optimizations_generated': len(optimizations),
                'optimizations_applied': len([o for o in optimizations if self._can_auto_apply(o)])
            },
            'top_issues': [
                {
                    'type': i.issue_type,
                    'severity': i.severity,
                    'description': i.description,
                    'recommendation': i.recommendation
                }
                for i in issues[:10]
            ],
            'optimizations': [
                {
                    'category': o.category,
                    'action': o.action,
                    'priority': o.priority,
                    'auto_applied': self._can_auto_apply(o)
                }
                for o in optimizations
            ]
        }
        
        # 保存报告
        filename = f"reports/optimization_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"报告已保存: {filename}")
```

---

## 6. 部署脚本

```bash
#!/bin/bash
# scripts/deploy_simulation.sh

set -e

echo "🚀 OPC200 大规模仿真测试环境部署"
echo "=================================="
echo ""

# 配置
LOCAL_AGENTS=150
CLOUD_AGENTS=50
DURATION_HOURS=168  # 7天

# 1. 检查依赖
echo "1. 检查依赖..."
docker --version
kubectl version --client
python3 --version

# 2. 启动本地实例池
echo "2. 启动本地实例池 (${LOCAL_AGENTS}个)..."
docker-compose -f docker-compose.simulation.yml up -d --scale agent-local=${LOCAL_AGENTS}

# 3. 部署云端实例池
echo "3. 部署云端实例池 (${CLOUD_AGENTS}个)..."
kubectl apply -f k8s/cloud-agents.yaml
kubectl wait deployment/opc-cloud-agents --for=condition=available --timeout=300s

# 4. 启动观测系统
echo "4. 启动观测系统..."
docker-compose -f docker-compose.observability.yml up -d

# 5. 初始化负载生成器
echo "5. 初始化负载生成器..."
python3 simulation/load_generator.py --agents ${LOCAL_AGENTS} --mode local &
python3 simulation/load_generator.py --agents ${CLOUD_AGENTS} --mode cloud &

# 6. 启动混沌工程
echo "6. 启动混沌工程..."
python3 simulation/chaos_engine.py --duration ${DURATION_HOURS} &

# 7. 启动自动优化引擎
echo "7. 启动自动优化引擎..."
python3 simulation/auto_optimizer.py &

echo ""
echo "✅ 仿真环境部署完成!"
echo ""
echo "访问监控面板:"
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "运行时长: ${DURATION_HOURS}小时"
echo ""

# 等待指定时间
sleep ${DURATION_HOURS}h

# 清理
echo "正在清理环境..."
docker-compose -f docker-compose.simulation.yml down
kubectl delete -f k8s/cloud-agents.yaml

echo "✅ 仿真测试完成"
```

---

## 7. 快速开始

### 7.1 一键部署

```bash
# 克隆配置
git clone https://github.com/coidea-ai/OPC200-simulation.git
cd OPC200-simulation

# 部署全量环境
./scripts/deploy_simulation.sh

# 或使用简化版本（本地20个实例测试）
./scripts/deploy_simulation.sh --local-only --agents 20 --duration 1
```

### 7.2 监控命令

```bash
# 查看实例状态
docker-compose ps
kubectl get pods -n opc-simulation

# 查看实时指标
curl http://localhost:9090/api/v1/query?query=opc_skill_invocations_total

# 查看优化报告
ls -la reports/optimization_report_*.json
```

---

*架构版本: 1.0*  
*目标: 200实例, 7×24小时, 自动化优化闭环*
