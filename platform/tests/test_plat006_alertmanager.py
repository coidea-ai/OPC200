#!/usr/bin/env python3
"""
PLAT-006: Alertmanager 离线告警集成测试

测试完整链路：
1. 推送指标 → 2. 验证在线 → 3. 删除指标(模拟离线) → 4. 等待告警触发 → 5. 验证邮件通知
"""
import requests
import time
import sys
import argparse
from datetime import datetime

PUSHGATEWAY = "http://localhost:9091"
PROMETHEUS = "http://localhost:9090"
ALERTMANAGER = "http://localhost:9093"

class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    ERR = "\033[91m"
    INFO = "\033[94m"
    END = "\033[0m"


def log_ok(msg): print(f"{Colors.OK}[OK]{Colors.END} {msg}")
def log_warn(msg): print(f"{Colors.WARN}[Colors.END} {msg}")
def log_err(msg): print(f"{Colors.ERR}[ERR]{Colors.END} {msg}")
def log_info(msg): print(f"{Colors.INFO}[INFO]{Colors.END} {msg}")


def push_metrics(tenant_id):
    metrics = f'''# HELP agent_health Agent health
# TYPE agent_health gauge
agent_health{{tenant_id="{tenant_id}",agent_version="2.0.0",os="linux"}} 1
# HELP cpu_usage CPU usage
# TYPE cpu_usage gauge
cpu_usage{{tenant_id="{tenant_id}"}} 45.0
'''
    url = f"{PUSHGATEWAY}/metrics/job/{tenant_id}"
    try:
        resp = requests.put(url, data=metrics, headers={"Content-Type": "text/plain"}, timeout=10)
        if resp.status_code == 200:
            log_ok(f"指标推送成功: {tenant_id}")
            return True
        else:
            log_err(f"推送失败 HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        log_err(f"推送异常: {e}")
        return False


def delete_metrics(tenant_id):
    url = f"{PUSHGATEWAY}/metrics/job/{tenant_id}"
    try:
        resp = requests.delete(url, timeout=10)
        if resp.status_code == 200:
            log_ok(f"指标删除成功(模拟离线): {tenant_id}")
            return True
        else:
            log_warn(f"删除返回 HTTP {resp.status_code}（可能指标已不存在）")
            return True
    except Exception as e:
        log_err(f"删除异常: {e}")
        return False


def check_prometheus_has_data(tenant_id, timeout=30):
    log_info(f"等待 Prometheus 抓取数据（最多 {timeout} 秒）...")
    url = f"{PROMETHEUS}/api/v1/query"
    query = f'agent_health{{tenant_id="{tenant_id}"}}'
    for i in range(timeout):
        try:
            resp = requests.get(url, params={"query": query}, timeout=5)
            data = resp.json()
            if data.get("data", {}).get("result"):
                log_ok("Prometheus 已抓取到指标数据")
                return True
        except:
            pass
        time.sleep(1)
        if i % 5 == 0 and i > 0:
            print(f"  等待中... {i}/{timeout}")
    log_warn("Prometheus 未抓取到数据（继续测试）")
    return False


def check_alertmanager_has_alert(tenant_id, timeout=120):
    log_info(f"等待告警触发（最多 {timeout} 秒）...")
    url = f"{ALERTMANAGER}/api/v2/alerts"
    for i in range(timeout):
        try:
            resp = requests.get(url, timeout=5)
            alerts = resp.json()
            for alert in alerts:
                labels = alert.get("labels", {})
                state = alert.get("status", {}).get("state", "")
                if labels.get("job") == tenant_id:
                    log_ok(f"Alertmanager 收到告警: {labels.get('alertname', 'N/A')} [{state}]")
                    log_info(f"  详情: {alert.get('annotations', {})}")
                    return True
        except:
            pass
        time.sleep(1)
        if i % 10 == 0:
            print(f"  等待中... {i}/{timeout}")
    log_err("Alertmanager 未收到告警")
    return False


def check_alertmanager_email_config():
    log_info("检查 Alertmanager 邮件配置...")
    try:
        resp = requests.get(f"{ALERTMANAGER}/api/v2/status", timeout=5)
        data = resp.json()
        config = data.get("config", {})
        receivers = config.get("receivers", [])
        email_count = sum(1 for r in receivers if r.get("email_configs"))
        if email_count > 0:
            log_ok(f"发现 {email_count} 个邮件接收器配置")
            for r in receivers:
                if r.get("email_configs"):
                    log_info(f"  - {r.get('name')}")
            return True
        else:
            log_warn("未发现邮件接收器")
            return False
    except Exception as e:
        log_err(f"检查配置失败: {e}")
        return False


def show_prometheus_rules():
    log_info("检查 Prometheus 告警规则...")
    try:
        resp = requests.get(f"{PROMETHEUS}/api/v1/rules", timeout=5)
        data = resp.json()
        groups = data.get("data", {}).get("groups", [])
        log_ok(f"发现 {len(groups)} 个规则组")
        for g in groups:
            rules = [r for r in g.get("rules", []) if r.get("type") == "alerting"]
            log_info(f"  组 '{g.get('name')}': {len(rules)} 条告警规则")
            for r in rules[:3]:
                print(f"    - {r.get('name')}: {r.get('query', '')[:55]}...")
        return True
    except Exception as e:
        log_err(f"获取规则失败: {e}")
        return False


def check_email_sent(tenant_id, timeout=60):
    """检查 Alertmanager 是否尝试发送过邮件通知"""
    log_info(f"检查邮件通知状态（最多 {timeout} 秒）...")
    # 通过 Alertmanager 的 API 查看特定告警的通知状态较困难，
    # 这里通过检查告警是否处于 active 且未被抑制来判断
    url = f"{ALERTMANAGER}/api/v2/alerts"
    for i in range(timeout):
        try:
            resp = requests.get(url, timeout=5)
            alerts = resp.json()
            for alert in alerts:
                labels = alert.get("labels", {})
                if labels.get("job") == tenant_id:
                    status = alert.get("status", {})
                    if status.get("state") == "active":
                        log_ok("告警处于 active 状态，邮件通知应已派发或排队中")
                        return True
        except:
            pass
        time.sleep(1)
    log_warn("无法直接确认邮件发送状态，请查看邮箱和 Alertmanager 日志")
    return False


def main():
    parser = argparse.ArgumentParser(description='PLAT-006 Alertmanager 集成测试')
    parser.add_argument('--tenant', '-t', default='test-plat006')
    parser.add_argument('--wait', '-w', type=int, default=45,
                       help='模拟离线等待秒数 (需大于规则阈值30秒)')
    parser.add_argument('--skip-cleanup', action='store_true')
    args = parser.parse_args()
    
    tenant = args.tenant
    print("=" * 60)
    print(f"PLAT-006 集成测试开始: {datetime.now()}")
    print(f"测试租户: {tenant}")
    print(f"模拟离线时长: {args.wait} 秒")
    print("=" * 60)
    
    check_alertmanager_email_config()
    show_prometheus_rules()
    
    print("\n" + "=" * 40)
    print("Step 1: 推送测试指标")
    print("=" * 40)
    if not push_metrics(tenant):
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("Step 2: 验证 Prometheus 抓取")
    print("=" * 40)
    check_prometheus_has_data(tenant)
    
    print("\n" + "=" * 40)
    print("Step 3: 删除指标模拟离线")
    print("=" * 40)
    delete_metrics(tenant)
    
    print("\n" + "=" * 40)
    print(f"Step 4: 等待 {args.wait} 秒模拟离线")
    print("=" * 40)
    for i in range(args.wait):
        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"  已离线 {i} 秒...")
    log_ok(f"离线 {args.wait} 秒完成")
    
    print("\n" + "=" * 40)
    print("Step 5: 验证告警触发")
    print("=" * 40)
    alert_ok = check_alertmanager_has_alert(tenant, timeout=90)
    
    print("\n" + "=" * 40)
    print("Step 6: 验证邮件通知状态")
    print("=" * 40)
    email_ok = check_email_sent(tenant, timeout=30)
    
    if not args.skip_cleanup:
        print("\n" + "=" * 40)
        print("Step 7: 清理测试数据")
        print("=" * 40)
        delete_metrics(tenant)
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    if alert_ok:
        log_ok("告警链路测试通过！")
        log_info("请检查 QQ 邮箱（包括垃圾箱）是否收到告警邮件")
        print("\n排查邮件命令:")
        print(f"  docker logs --since 5m opc200-alertmanager")
    else:
        log_err("告警链路测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
