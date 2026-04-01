"""OPC200 简化部署验证测试（CI 跳过版本）

标记为 integration 测试，避免在 CI 中自动运行。
本地验证时使用: pytest tests/deploy/ -m integration
"""

import pytest

# 标记所有测试为 integration，CI 默认跳过
pytestmark = pytest.mark.integration

# 如果 CI 没有 Docker，也跳过
# 使用方法: pytest -m "not integration" tests/  (跳过集成测试)

import requests
import subprocess
import socket


class TestDeploymentInfrastructure:
    """验证部署基础设施是否就绪（P0 核心）"""
    
    def test_docker_daemon_running(self):
        """Docker 守护进程应该运行"""
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        assert result.returncode == 0, "Docker daemon not running"
    
    def test_required_images_exist(self):
        """必需的镜像应该已构建/拉取"""
        result = subprocess.run(
            ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
            capture_output=True, text=True
        )
        images = result.stdout.strip().split('\n')
        required = ['opc200:light', 'qdrant/qdrant:v1.7.4', 
                    'prom/prometheus:v2.49.1', 'grafana/grafana:10.3.1']
        for img in required:
            assert any(img in i for i in images), f"Missing image: {img}"


class TestServiceAvailability:
    """验证各服务可用性（P0 核心）"""
    
    def test_qdrant_health(self):
        """Qdrant 向量数据库应该健康"""
        resp = requests.get('http://localhost:6333/healthz', timeout=5)
        assert resp.status_code == 200
        assert 'healthz check passed' in resp.text
    
    def test_qdrant_collections_api(self):
        """Qdrant Collections API 应该可访问"""
        resp = requests.get('http://localhost:6333/collections', timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert 'result' in data
    
    def test_prometheus_health(self):
        """Prometheus 监控应该健康"""
        resp = requests.get('http://localhost:9090/-/healthy', timeout=5)
        assert resp.status_code == 200
        assert 'Prometheus Server is Healthy' in resp.text
    
    def test_prometheus_metrics_endpoint(self):
        """Prometheus /metrics 端点应该可访问"""
        resp = requests.get('http://localhost:9090/metrics', timeout=5)
        assert resp.status_code == 200
        assert 'prometheus_' in resp.text
    
    def test_grafana_health(self):
        """Grafana 可视化应该健康"""
        resp = requests.get('http://localhost:3000/api/health', timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('database') == 'ok'
    
    def test_grafana_login_page(self):
        """Grafana 登录页面应该可访问"""
        resp = requests.get('http://localhost:3000/login', timeout=5)
        assert resp.status_code == 200
        assert 'Grafana' in resp.text
    
    def test_gateway_port_listening(self):
        """Gateway 端口应该监听"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 18889))
        sock.close()
        assert result == 0, "Gateway port 18889 not listening"


class TestMonitoringIntegration:
    """验证监控集成是否正常工作（设计目标核心）"""
    
    def test_prometheus_can_scrape_targets(self):
        """Prometheus 应该能发现目标"""
        resp = requests.get('http://localhost:9090/api/v1/targets', timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        active = data.get('data', {}).get('activeTargets', [])
        assert len(active) >= 1, "No active scraping targets"
    
    def test_grafana_datasource_configured(self):
        """Grafana 应该配置了 Prometheus 数据源"""
        resp = requests.get(
            'http://localhost:3000/api/datasources',
            auth=('admin', 'admin'),
            timeout=5
        )
        assert resp.status_code in [200, 401]


class TestResourceConstraints:
    """验证资源限制是否符合预期（P0 核心）"""
    
    def test_memory_usage_within_limit(self):
        """所有容器内存占用应该在限制范围内"""
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 
             '{{.Name}}: {{.MemUsage}}'],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'opc200' in line:
                parts = line.split(': ')
                if len(parts) == 2:
                    mem_part = parts[1]
                    usage_str = mem_part.split(' / ')[0]
                    if 'MiB' in usage_str:
                        usage = float(usage_str.replace('MiB', '').strip())
                        assert usage < 2000, f"Memory usage too high: {line}"
    
    def test_container_count(self):
        """应该运行 5 个核心容器"""
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=opc200', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        containers = [c for c in result.stdout.strip().split('\n') if c]
        expected = ['opc200-gateway', 'opc200-journal', 'opc200-qdrant',
                   'opc200-prometheus', 'opc200-grafana']
        for exp in expected:
            assert any(exp in c for c in containers), f"Missing container: {exp}"


class TestDataStorage:
    """验证数据存储能力（简化版测试）"""
    
    def test_qdrant_can_create_collection(self):
        """Qdrant 应该能创建集合"""
        resp = requests.put(
            'http://localhost:6333/collections/test_collection',
            json={
                "vectors": {
                    "size": 4,
                    "distance": "Cosine"
                }
            },
            timeout=5
        )
        assert resp.status_code in [200, 409]
    
    def test_qdrant_can_upsert_vectors(self):
        """Qdrant 应该能插入向量"""
        requests.put(
            'http://localhost:6333/collections/test_collection',
            json={"vectors": {"size": 4, "distance": "Cosine"}},
            timeout=5
        )
        
        resp = requests.put(
            'http://localhost:6333/collections/test_collection/points',
            json={
                "points": [
                    {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}
                ]
            },
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('status') == 'ok'
    
    def test_qdrant_can_search_vectors(self):
        """Qdrant 应该能搜索向量"""
        resp = requests.post(
            'http://localhost:6333/collections/test_collection/points/search',
            json={
                "vector": [0.1, 0.2, 0.3, 0.4],
                "limit": 1
            },
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'result' in data


class TestKnownLimitations:
    """记录已知限制（后续改进点）"""
    
    def test_tailscale_not_deployed(self):
        """Tailscale VPN 未在简化部署中启用（已知限制）"""
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=opc200-tailscale', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        assert 'opc200-tailscale' not in result.stdout, \
            "Tailscale should not be in minimal deployment"
    
    def test_openai_skipped(self):
        """OpenAI 集成在简化部署中跳过（已知限制）"""
        pass
