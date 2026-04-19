#!/usr/bin/env python3
"""
OPC200 Agent 模拟数据生成器
用于测试告警功能（离线检测）

用法：
    # 模拟 Agent 在线（持续推送）
    python mock_agent_data.py --tenant mock-001 --interval 60
    
    # 模拟 Agent 离线 N 秒后恢复
    python mock_agent_data.py --tenant mock-001 --offline 300
    
    # 删除推送的指标
    python mock_agent_data.py --tenant mock-001 --delete
"""

import time
import requests
import random
import argparse
import sys
import signal
from datetime import datetime


DEFAULT_PLATFORM_URL = "http://localhost:9091"
DEFAULT_INTERVAL = 60


def generate_metrics(tenant_id, os_type="linux"):
    """生成 Agent 在线时的模拟指标"""
    cpu = random.uniform(10, 60)
    memory = random.uniform(30, 70)
    disk = random.uniform(40, 80)
    
    return f'''# HELP agent_health Agent health status (1=healthy, 0=unhealthy)
# TYPE agent_health gauge
agent_health{{tenant_id="{tenant_id}",agent_version="2.0.0",os="{os_type}"}} 1
# HELP cpu_usage CPU usage percentage
# TYPE cpu_usage gauge
cpu_usage{{tenant_id="{tenant_id}"}} {cpu:.1f}
# HELP memory_usage Memory usage percentage
# TYPE memory_usage gauge
memory_usage{{tenant_id="{tenant_id}"}} {memory:.1f}
# HELP disk_usage Disk usage percentage
# TYPE disk_usage gauge
disk_usage{{tenant_id="{tenant_id}"}} {disk:.1f}
'''


def push_metrics(tenant_id, platform_url=DEFAULT_PLATFORM_URL, os_type="linux"):
    """推送指标到 Pushgateway（使用 PUT）"""
    metrics = generate_metrics(tenant_id, os_type)
    url = f"{platform_url}/metrics/job/{tenant_id}"
    
    try:
        response = requests.put(
            url,
            data=metrics,
            headers={"Content-Type": "text/plain; version=0.0.4"},
            timeout=10
        )
        success = response.status_code == 200
        if not success:
            print(f"  [WARN] Push failed: HTTP {response.status_code}")
            print(f"  [DETAIL] {response.text[:200]}")
        return success
    except requests.exceptions.ConnectionError:
        print(f"  [ERR] Cannot connect to {platform_url}")
        return False
    except Exception as e:
        print(f"  [ERR] Push error: {e}")
        return False


def delete_metrics(tenant_id, platform_url=DEFAULT_PLATFORM_URL):
    """删除 Pushgateway 中的指标"""
    url = f"{platform_url}/metrics/job/{tenant_id}"
    try:
        response = requests.delete(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"  [ERR] Delete error: {e}")
        return False


def simulate_offline(tenant_id, offline_duration, platform_url=DEFAULT_PLATFORM_URL):
    """模拟 Agent 离线指定时长"""
    print(f"\n[{tenant_id}] 模拟离线测试")
    print(f"  Step 1: 推送初始指标（在线状态）")
    
    if not push_metrics(tenant_id, platform_url):
        print(f"  [ERR] 初始推送失败，中止测试")
        return False
    
    print(f"  Step 2: 停止推送 {offline_duration} 秒（模拟离线）")
    start_time = datetime.now()
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for remaining in range(offline_duration, 0, -1):
        if remaining % 60 == 0 or remaining <= 10:
            mins, secs = divmod(remaining, 60)
            print(f"  剩余: {mins}分{secs}秒", end='\r')
        time.sleep(1)
    
    print(f"\n  Step 3: 恢复推送")
    if push_metrics(tenant_id, platform_url):
        print(f"  [{tenant_id}] 离线测试完成，已恢复在线")
        return True
    else:
        print(f"  [ERR] 恢复推送失败")
        return False


def run_continuous(tenant_id, interval, platform_url=DEFAULT_PLATFORM_URL, os_type="linux"):
    """持续运行，模拟正常在线 Agent"""
    print(f"\n[{tenant_id}] 持续推送模式（间隔 {interval} 秒）")
    print(f"目标: {platform_url}")
    print("按 Ctrl+C 停止\n")
    
    running = True
    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print(f"\n[{tenant_id}] 收到停止信号，正在退出...")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    push_count = 0
    while running:
        timestamp = datetime.now().strftime('%H:%M:%S')
        if push_metrics(tenant_id, platform_url, os_type):
            push_count += 1
            print(f"[{timestamp}] [{tenant_id}] 推送成功 (#{push_count})")
        else:
            print(f"[{timestamp}] [{tenant_id}] 推送失败")
        
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)
    
    print(f"[{tenant_id}] 已停止，共推送 {push_count} 次")


def main():
    parser = argparse.ArgumentParser(
        description='OPC200 Agent 模拟数据生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python mock_agent_data.py --tenant opc-test-001
  python mock_agent_data.py --tenant opc-test-001 --offline 300
  python mock_agent_data.py --tenant opc-test-001 --delete
        '''
    )
    
    parser.add_argument('--tenant', '-t', default='mock-001',
                       help='租户 ID (默认: mock-001)')
    parser.add_argument('--platform', '-p', default=DEFAULT_PLATFORM_URL,
                       help=f'Pushgateway URL (默认: {DEFAULT_PLATFORM_URL})')
    parser.add_argument('--interval', '-i', type=int, default=DEFAULT_INTERVAL,
                       help=f'推送间隔秒数 (默认: {DEFAULT_INTERVAL})')
    parser.add_argument('--offline', '-o', type=int, metavar='SECONDS',
                       help='模拟离线 N 秒后恢复')
    parser.add_argument('--delete', '-d', action='store_true',
                       help='删除该 tenant 的指标')
    parser.add_argument('--os', default='linux',
                       choices=['linux', 'windows', 'darwin'],
                       help='操作系统类型')
    
    args = parser.parse_args()
    
    if args.delete:
        print(f"删除 {args.tenant} 的指标...")
        if delete_metrics(args.tenant, args.platform):
            print("删除成功")
        else:
            print("删除失败或指标不存在")
        return
    
    # 验证平台可连接
    try:
        requests.get(args.platform, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"[ERR] 无法连接到 {args.platform}")
        print("请确认：")
        print("  1. Pushgateway 是否已启动")
        print("  2. 地址和端口是否正确")
        sys.exit(1)
    
    if args.offline:
        simulate_offline(args.tenant, args.offline, args.platform)
    else:
        run_continuous(args.tenant, args.interval, args.platform, args.os)


if __name__ == "__main__":
    main()
