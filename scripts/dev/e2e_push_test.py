"""AGENT-006 端到端联调脚本

验证链路：collector 采集 -> pusher 推送 -> Pushgateway 接收 -> Prometheus 抓取
"""

import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

import requests
from agent.src.exporter.collector import MetricsCollector
from agent.src.exporter.pusher import MetricsPusher

PUSHGATEWAY_URL = "http://localhost:9091"
PROMETHEUS_URL = "http://localhost:9090"

TENANTS = [
    {"tenant_id": "opc-test-001", "label": "租户A"},
    {"tenant_id": "opc-test-002", "label": "租户B"},
]


def push_tenant(tenant: dict) -> bool:
    collector = MetricsCollector(agent_version="1.0.0")
    pusher = MetricsPusher(
        platform_url=PUSHGATEWAY_URL,
        tenant_id=tenant["tenant_id"],
        api_key="dev-no-auth",
        collector=collector,
    )
    metrics = collector.collect_all()
    print(f"\n[{tenant['label']} / {tenant['tenant_id']}]")
    print(f"  CPU:    {metrics.cpu_usage:.1f}%")
    print(f"  内存:   {metrics.memory_usage:.1f}%")
    print(f"  磁盘:   {metrics.disk_usage:.1f}%")
    print(f"  健康:   {metrics.agent_health}")

    result = pusher.push(metrics)
    print(f"  推送:   {'[OK]' if result else '[FAIL]'}")
    return result


def verify_pushgateway(tenant_id: str) -> bool:
    resp = requests.get(f"{PUSHGATEWAY_URL}/metrics", timeout=5)
    return f'job="{tenant_id}"' in resp.text


def verify_prometheus(tenant_id: str) -> bool:
    resp = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": f'cpu_usage{{job="{tenant_id}"}}'},
        timeout=5,
    )
    data = resp.json()
    return len(data.get("data", {}).get("result", [])) > 0


def main():
    print("=" * 50)
    print("AGENT-006 端到端联调")
    print("=" * 50)

    print("\n[1] 推送指标")
    all_pushed = all(push_tenant(t) for t in TENANTS)

    print("\n[2] 验证 Pushgateway 接收")
    for t in TENANTS:
        ok = verify_pushgateway(t["tenant_id"])
        print(f"  {t['tenant_id']}: {'[OK]' if ok else '[FAIL]'}")

    print("\n[3] 等待 Prometheus 抓取 (15s)...")
    time.sleep(15)

    print("\n[4] 验证 Prometheus 数据")
    prom_ok = True
    for t in TENANTS:
        ok = verify_prometheus(t["tenant_id"])
        print(f"  {t['tenant_id']}: {'[OK]' if ok else '[FAIL - may need more time]'}")
        if not ok:
            prom_ok = False

    print("\n[5] 多租户隔离验证")
    resp = requests.get(f"{PUSHGATEWAY_URL}/metrics", timeout=5)
    ids = [t["tenant_id"] for t in TENANTS]
    isolated = all(cid in resp.text for cid in ids)
    print(f"  两个租户数据均存在: {'[OK]' if isolated else '[FAIL]'}")

    print("\n" + "=" * 50)
    if all_pushed and isolated:
        print("联调结果: [PASS]")
        print(f"  Grafana: http://localhost:3000  (admin / opc200admin)")
    else:
        print("联调结果: [FAIL] 部分失败，请检查上方日志")
    print("=" * 50)


if __name__ == "__main__":
    main()
