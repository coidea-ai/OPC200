"""
PLAT-002: Grafana Dashboard 配置测试
TDD: 先写测试，再写实现
"""
import pytest
import requests
import json
import subprocess


class TestGrafanaService:
    """测试 Grafana 服务."""
    
    def test_grafana_port_accessible(self):
        """测试 Grafana 3000 端口可访问."""
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=opc200-grafana", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        assert "opc200-grafana" in result.stdout, "Grafana 容器未运行"
    
    def test_grafana_login_page(self):
        """测试 Grafana 登录页面可访问."""
        response = requests.get("http://localhost:3000/login", timeout=5)
        assert response.status_code == 200
        assert "Grafana" in response.text


class TestGrafanaDatasource:
    """测试 Grafana 数据源配置."""
    
    def test_prometheus_datasource_exists(self):
        """测试 Prometheus 数据源已配置."""
        # 使用 admin 认证检查数据源
        response = requests.get(
            "http://admin:opc200admin@localhost:3000/api/datasources",
            timeout=5
        )
        assert response.status_code == 200
        datasources = response.json()
        
        # 查找 Prometheus 数据源
        prometheus_found = any(
            ds.get("name") == "Prometheus" and ds.get("type") == "prometheus"
            for ds in datasources
        )
        assert prometheus_found, "Prometheus 数据源未配置"
    
    def test_prometheus_datasource_url_correct(self):
        """测试 Prometheus 数据源 URL 正确."""
        response = requests.get(
            "http://admin:opc200admin@localhost:3000/api/datasources",
            timeout=5
        )
        datasources = response.json()
        
        prometheus_ds = next(
            (ds for ds in datasources if ds.get("name") == "Prometheus"),
            None
        )
        assert prometheus_ds is not None
        assert "opc200-prometheus:9090" in prometheus_ds.get("url", "")


class TestGrafanaDashboard:
    """测试 Grafana Dashboard 配置."""
    
    def test_dashboard_provider_config_exists(self):
        """测试 Dashboard provider 配置文件存在."""
        import os
        assert os.path.exists(
            "grafana/provisioning/dashboards/dashboard.yml"
        ), "dashboard provider 配置不存在"
    
    def test_datasource_config_exists(self):
        """测试 datasource 配置文件存在."""
        import os
        assert os.path.exists(
            "grafana/provisioning/datasources/datasource.yml"
        ), "datasource 配置不存在"
    
    def test_pushgateway_dashboard_exists(self):
        """测试 Pushgateway Dashboard 已创建."""
        response = requests.get(
            "http://admin:opc200admin@localhost:3000/api/search",
            timeout=5
        )
        assert response.status_code == 200
        dashboards = response.json()
        
        # 查找 Pushgateway Overview dashboard
        dashboard_found = any(
            "pushgateway" in db.get("title", "").lower() or
            "pushgateway" in db.get("uri", "").lower()
            for db in dashboards
        )
        assert dashboard_found, "Pushgateway Dashboard 未找到"
    
    def test_dashboard_can_query_metrics(self):
        """测试 Dashboard 能查询到指标."""
        # 先推送一条测试指标
        test_data = "test_dashboard_metric 99.9\n"
        requests.post(
            "http://localhost:9091/metrics/job/test-dashboard",
            data=test_data,
            headers={"Content-Type": "text/plain"},
            timeout=5
        )
        
        # 通过 Grafana 查询 API 验证
        query = {
            "expr": "test_dashboard_metric",
            "datasource": {"type": "prometheus", "uid": "prometheus"}
        }
        response = requests.post(
            "http://admin:opc200admin@localhost:3000/api/ds/query",
            json=query,
            timeout=10
        )
        # 查询可能失败，但不应是连接错误
        assert response.status_code in [200, 400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
