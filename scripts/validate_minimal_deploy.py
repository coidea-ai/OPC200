#!/usr/bin/env python3
"""OPC200 简化部署验证脚本（无需 pytest）

直接运行验证部署状态
"""

import subprocess
import requests
import socket
import sys


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'


def run_check(name, check_func):
    """运行单个检查并打印结果"""
    try:
        check_func()
        print(f"{Colors.GREEN}✅ PASS{Colors.RESET} {name}")
        return True
    except AssertionError as e:
        print(f"{Colors.RED}❌ FAIL{Colors.RESET} {name}: {e}")
        return False
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  ERROR{Colors.RESET} {name}: {e}")
        return False


def check_docker_daemon():
    """检查 Docker 守护进程"""
    result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
    assert result.returncode == 0, "Docker daemon not running"


def check_required_images():
    """检查必需的镜像"""
    result = subprocess.run(
        ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
        capture_output=True, text=True
    )
    images = result.stdout.strip().split('\n')
    required = ['opc200:light', 'qdrant/qdrant:v1.7.4',
                'prom/prometheus:v2.49.1', 'grafana/grafana:10.3.1']
    for img in required:
        assert any(img in i for i in images), f"Missing image: {img}"


def check_qdrant_health():
    """检查 Qdrant 健康"""
    resp = requests.get('http://localhost:6333/healthz', timeout=5)
    assert resp.status_code == 200, f"Status: {resp.status_code}"
    assert 'healthz check passed' in resp.text


def check_qdrant_api():
    """检查 Qdrant API"""
    resp = requests.get('http://localhost:6333/collections', timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert 'result' in data


def check_prometheus_health():
    """检查 Prometheus 健康"""
    resp = requests.get('http://localhost:9090/-/healthy', timeout=5)
    assert resp.status_code == 200
    assert 'Prometheus Server is Healthy' in resp.text


def check_prometheus_metrics():
    """检查 Prometheus 指标"""
    resp = requests.get('http://localhost:9090/metrics', timeout=5)
    assert resp.status_code == 200
    assert 'prometheus_' in resp.text


def check_grafana_health():
    """检查 Grafana 健康"""
    resp = requests.get('http://localhost:3000/api/health', timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('database') == 'ok'


def check_grafana_login():
    """检查 Grafana 登录页"""
    resp = requests.get('http://localhost:3000/login', timeout=5)
    assert resp.status_code == 200
    assert 'Grafana' in resp.text


def check_gateway_port():
    """检查 Gateway 端口"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('localhost', 18889))
    sock.close()
    assert result == 0, "Port 18889 not listening"


def check_container_count():
    """检查容器数量"""
    result = subprocess.run(
        ['docker', 'ps', '--filter', 'name=opc200', '--format', '{{.Names}}'],
        capture_output=True, text=True
    )
    containers = [c for c in result.stdout.strip().split('\n') if c]
    expected = ['opc200-gateway', 'opc200-journal', 'opc200-qdrant',
               'opc200-prometheus', 'opc200-grafana']
    for exp in expected:
        assert any(exp in c for c in containers), f"Missing: {exp}"


def check_qdrant_vector_ops():
    """检查 Qdrant 向量操作"""
    # 创建集合
    resp = requests.put(
        'http://localhost:6333/collections/validate_test',
        json={"vectors": {"size": 4, "distance": "Cosine"}},
        timeout=5
    )
    assert resp.status_code in [200, 409]  # 创建或已存在
    
    # 插入向量
    resp = requests.put(
        'http://localhost:6333/collections/validate_test/points',
        json={"points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
        timeout=5
    )
    assert resp.status_code == 200
    
    # 搜索
    resp = requests.post(
        'http://localhost:6333/collections/validate_test/points/search',
        json={"vector": [0.1, 0.2, 0.3, 0.4], "limit": 1},
        timeout=5
    )
    assert resp.status_code == 200


def check_tailscale_not_deployed():
    """确认 Tailscale 未部署（已知限制）"""
    result = subprocess.run(
        ['docker', 'ps', '--filter', 'name=opc200-tailscale', '--format', '{{.Names}}'],
        capture_output=True, text=True
    )
    assert 'opc200-tailscale' not in result.stdout


def main():
    print("=" * 60)
    print("OPC200 简化部署验证测试")
    print("=" * 60)
    print()
    
    checks = [
        ("Docker 守护进程", check_docker_daemon),
        ("必需镜像存在", check_required_images),
        ("Qdrant 健康检查", check_qdrant_health),
        ("Qdrant API 可访问", check_qdrant_api),
        ("Prometheus 健康", check_prometheus_health),
        ("Prometheus 指标", check_prometheus_metrics),
        ("Grafana 健康", check_grafana_health),
        ("Grafana 登录页", check_grafana_login),
        ("Gateway 端口监听", check_gateway_port),
        ("5 个容器运行中", check_container_count),
        ("Qdrant 向量操作", check_qdrant_vector_ops),
        ("Tailscale 未部署（已知限制）", check_tailscale_not_deployed),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_func in checks:
        if run_check(name, check_func):
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"结果: {Colors.GREEN}{passed} 通过{Colors.RESET}, "
          f"{Colors.RED}{failed} 失败{Colors.RESET}, "
          f"共 {passed + failed} 项")
    print("=" * 60)
    
    if failed == 0:
        print(f"{Colors.GREEN}✅ 所有验证通过！简化部署工作正常。{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}❌ 有 {failed} 项验证失败，请检查。{Colors.RESET}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
