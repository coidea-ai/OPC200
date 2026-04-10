"""
PLAT-001: Prometheus + Pushgateway 基础设施测试
TDD: 先写测试，再写实现
"""
import pytest
import requests
import subprocess
import time


class TestPushgatewayService:
    """测试 Pushgateway 服务."""
    
    def test_pushgateway_port_accessible(self):
        """测试 Pushgateway 9091 端口可访问."""
        # 服务启动后，检查端口是否监听
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=opc200-pushgateway", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        assert "opc200-pushgateway" in result.stdout, "Pushgateway 容器未运行"
    
    def test_pushgateway_metrics_endpoint(self):
        """测试 /metrics 端点可访问."""
        response = requests.get("http://localhost:9091/metrics", timeout=5)
        assert response.status_code == 200
        assert "pushgateway_" in response.text
    
    def test_pushgateway_receive_push(self):
        """测试能接收指标推送."""
        # 推送测试指标（必须以换行结尾）
        test_data = "test_metric{instance=\"test\"} 42.0\n"
        response = requests.post(
            "http://localhost:9091/metrics/job/test-job",
            data=test_data,
            headers={"Content-Type": "text/plain"},
            timeout=5
        )
        assert response.status_code == 200, f"推送失败: {response.status_code} - {response.text}"
        
        # 验证指标已接收
        response = requests.get("http://localhost:9091/metrics", timeout=5)
        assert "test_metric" in response.text


class TestPrometheusService:
    """测试 Prometheus 服务."""
    
    def test_prometheus_port_accessible(self):
        """测试 Prometheus 9090 端口可访问."""
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=opc200-prometheus", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        assert "opc200-prometheus" in result.stdout, "Prometheus 容器未运行"
    
    def test_prometheus_web_interface(self):
        """测试 Prometheus Web 界面可访问."""
        response = requests.get("http://localhost:9090", timeout=5)
        assert response.status_code == 200
        assert "Prometheus" in response.text
    
    def test_prometheus_scraping_pushgateway(self):
        """测试 Prometheus 正在抓取 Pushgateway."""
        # 检查 targets 页面
        response = requests.get("http://localhost:9090/api/v1/targets", timeout=5)
        assert response.status_code == 200
        data = response.json()
        
        # 查找 pushgateway target
        active_targets = data.get("data", {}).get("activeTargets", [])
        pushgateway_found = any(
            "pushgateway" in str(t.get("labels", {})).lower() 
            for t in active_targets
        )
        assert pushgateway_found, "Prometheus 未配置抓取 Pushgateway"


class TestDockerCompose:
    """测试 Docker Compose 配置."""
    
    def test_docker_compose_file_exists(self):
        """测试 docker-compose.yml 存在."""
        import os
        assert os.path.exists("docker-compose.yml"), "docker-compose.yml 不存在"
    
    def test_prometheus_config_exists(self):
        """测试 Prometheus 配置文件存在."""
        import os
        assert os.path.exists("prometheus/prometheus.yml"), "prometheus.yml 不存在"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
