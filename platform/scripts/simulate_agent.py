#!/usr/bin/env python3
"""
模拟 Agent 指标推送脚本
用于测试 PLAT-006 告警功能

用法:
    python3 simulate_agent.py --tenant opc-001 --action start   # 开始推送
    python3 simulate_agent.py --tenant opc-001 --action stop    # 停止推送（模拟离线）
    python3 simulate_agent.py --tenant opc-001 --action high-cpu  # 模拟高 CPU
"""

import argparse
import time
import requests
import signal
import sys
from datetime import datetime

PUSHGATEWAY_URL = "http://opc200.meerkatai.cn:9091"
INTERVAL = 60  # 推送间隔（秒）

# 模拟数据模板
METRICS_TEMPLATE = """# HELP agent_health Agent 健康状态 (1=健康, 0=异常)
# TYPE agent_health gauge
agent_health{{tenant_id="{tenant_id}",agent_version="1.0.0",os="linux"}} {health}

# HELP cpu_usage CPU 使用率
# TYPE cpu_usage gauge
cpu_usage{{tenant_id="{tenant_id}"}} {cpu}

# HELP memory_usage 内存使用率
# TYPE memory_usage gauge
memory_usage{{tenant_id="{tenant_id}"}} {memory}

# HELP disk_usage 磁盘使用率
# TYPE disk_usage gauge
disk_usage{{tenant_id="{tenant_id}"}} {disk}

# HELP push_timestamp 上次推送时间戳
# TYPE push_timestamp gauge
push_timestamp{{tenant_id="{tenant_id}"}} {timestamp}
"""

running = True


def signal_handler(sig, frame):
    """处理 Ctrl+C"""
    global running
    print(f"\n[{datetime.now()}] 停止模拟 Agent: {args.tenant}")
    running = False


def push_metrics(tenant_id, health=1, cpu=45.0, memory=60.0, disk=50.0):
    """推送指标到 Pushgateway"""
    metrics = METRICS_TEMPLATE.format(
        tenant_id=tenant_id,
        health=health,
        cpu=cpu,
        memory=memory,
        disk=disk,
        timestamp=int(time.time())
    )
    
    url = f"{PUSHGATEWAY_URL}/metrics/job/opc-agent/instance/{tenant_id}"
    
    try:
        response = requests.post(
            url,
            data=metrics,
            headers={"Content-Type": "text/plain"},
            timeout=10
        )
        if response.status_code == 200:
            print(f"[{datetime.now()}] ✓ {tenant_id} 指标推送成功")
            return True
        else:
            print(f"[{datetime.now()}] ✗ {tenant_id} 推送失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] ✗ {tenant_id} 推送异常: {e}")
        return False


def delete_metrics(tenant_id):
    """删除指标（模拟 Agent 离线）"""
    url = f"{PUSHGATEWAY_URL}/metrics/job/opc-agent/instance/{tenant_id}"
    
    try:
        response = requests.delete(url, timeout=10)
        if response.status_code == 200:
            print(f"[{datetime.now()}] ✓ {tenant_id} 指标已删除（模拟离线）")
            return True
        else:
            print(f"[{datetime.now()}] ✗ {tenant_id} 删除失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] ✗ {tenant_id} 删除异常: {e}")
        return False


def simulate_online(tenant_id):
    """模拟 Agent 在线状态（正常推送）"""
    global running
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[{datetime.now()}] 开始模拟 Agent: {tenant_id}")
    print(f"[{datetime.now()}] 推送地址: {PUSHGATEWAY_URL}")
    print(f"[{datetime.now()}] 推送间隔: {INTERVAL}秒")
    print(f"[{datetime.now()}] 按 Ctrl+C 停止\n")
    
    while running:
        push_metrics(tenant_id)
        time.sleep(INTERVAL)


def simulate_offline(tenant_id):
    """模拟 Agent 离线"""
    print(f"[{datetime.now()}] 模拟 Agent 离线: {tenant_id}")
    delete_metrics(tenant_id)
    print(f"[{datetime.now()}] 等待 6 分钟观察告警触发...")
    print(f"[{datetime.now()}] 检查 Alertmanager: http://100.74.18.112:9093")


def simulate_high_cpu(tenant_id):
    """模拟 CPU 过高"""
    global running
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[{datetime.now()}] 模拟 Agent 高 CPU: {tenant_id}")
    print(f"[{datetime.now()}] CPU 将保持在 85%+\n")
    
    while running:
        # 模拟 85-95% CPU
        cpu = 85.0 + (int(time.time()) % 10)
        push_metrics(tenant_id, cpu=cpu)
        time.sleep(INTERVAL)


def simulate_high_memory(tenant_id):
    """模拟内存过高"""
    global running
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[{datetime.now()}] 模拟 Agent 高内存: {tenant_id}")
    print(f"[{datetime.now()}] 内存将保持在 90%+\n")
    
    while running:
        push_metrics(tenant_id, memory=90.0 + (int(time.time()) % 5))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="模拟 OPC200 Agent 指标推送")
    parser.add_argument("--tenant", required=True, help="租户 ID (如: opc-001)")
    parser.add_argument("--action", required=True, 
                       choices=["start", "stop", "high-cpu", "high-memory"],
                       help="操作类型")
    
    args = parser.parse_args()
    
    if args.action == "start":
        simulate_online(args.tenant)
    elif args.action == "stop":
        simulate_offline(args.tenant)
    elif args.action == "high-cpu":
        simulate_high_cpu(args.tenant)
    elif args.action == "high-memory":
        simulate_high_memory(args.tenant)
