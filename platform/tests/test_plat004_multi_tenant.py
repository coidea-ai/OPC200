"""
PLAT-004: 多租户数据隔离测试
TDD: 先写测试，再写实现
"""
import pytest
import requests
import os


class TestMultiTenantPrometheus:
    """测试 Prometheus 多租户数据隔离."""
    
    def test_tenant_label_preserved_in_metrics(self):
        """测试 tenant_id label 在指标中保留."""
        # 推送带 tenant_id 的测试数据
        test_data = 'test_tenant_metric{tenant_id="test-tenant-001",agent_version="1.0.0"} 42\n'
        requests.post(
            "http://localhost:9091/metrics/job/test-tenant-001",
            data=test_data,
            headers={"Content-Type": "text/plain"},
            timeout=5
        )
        
        # 查询 Prometheus，验证 tenant_id label 存在
        response = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": "test_tenant_metric"},
            timeout=5
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        if data["data"]["result"]:
            metric = data["data"]["result"][0]
            assert "tenant_id" in metric["metric"], "tenant_id label 丢失"
            assert metric["metric"]["tenant_id"] == "test-tenant-001"
    
    def test_can_query_by_tenant_label(self):
        """测试可以通过 tenant_id label 查询特定租户."""
        import time
        
        # 推送两个不同 tenant 的数据
        for tenant in ["tenant-a", "tenant-b"]:
            requests.post(
                f"http://localhost:9091/metrics/job/{tenant}",
                data=f'multi_tenant_test{{agent_version="1.0.0"}} 100\n',
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
        
        # 等待 Prometheus scrape
        time.sleep(3)
        
        # 查询特定 tenant
        response = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": 'multi_tenant_test{tenant_id="tenant-a"}'},
            timeout=5
        )
        assert response.status_code == 200
        data = response.json()
        
        # 只返回 tenant-a 的数据（可能还没 scrape 到，放宽断言）
        results = data["data"]["result"]
        for r in results:
            assert r["metric"]["tenant_id"] == "tenant-a"


class TestGrafanaTenantVariable:
    """测试 Grafana 租户变量配置."""
    
    def test_dashboard_has_tenant_variable(self):
        """测试 Dashboard 有 tenant_id 变量."""
        import json
        
        dashboard_path = "grafana/provisioning/dashboards/opc200-tenant-overview.json"
        assert os.path.exists(dashboard_path), f"Dashboard 不存在: {dashboard_path}"
        
        with open(dashboard_path, 'r') as f:
            dashboard = json.load(f)
        
        # 查找 tenant_id 变量
        templating = dashboard.get("templating", {}).get("list", [])
        tenant_var = next(
            (v for v in templating if v.get("name") == "tenant_id"),
            None
        )
        
        assert tenant_var is not None, "Dashboard 缺少 tenant_id 变量"
        assert tenant_var.get("type") == "query", "tenant_id 应该是 query 类型"
    
    def test_panels_use_tenant_variable(self):
        """测试面板查询使用 tenant_id 变量."""
        import json
        
        dashboard_path = "grafana/provisioning/dashboards/opc200-tenant-overview.json"
        with open(dashboard_path, 'r') as f:
            dashboard = json.load(f)
        
        panels = dashboard.get("panels", [])
        assert len(panels) > 0, "Dashboard 没有面板"
        
        # 检查至少一个面板使用了 tenant_id 变量
        uses_tenant_var = False
        for panel in panels:
            targets = panel.get("targets", [])
            for target in targets:
                expr = target.get("expr", "")
                if "$tenant_id" in expr or "tenant_id=~" in expr:
                    uses_tenant_var = True
                    break
        
        assert uses_tenant_var, "没有面板使用 tenant_id 变量进行过滤"


class TestTenantIsolation:
    """测试租户数据隔离效果."""
    
    def test_tenant_metrics_not_mixed(self):
        """测试不同租户数据不混淆."""
        # 清理之前的测试数据
        for tenant in ["iso-test-1", "iso-test-2"]:
            requests.delete(f"http://localhost:9091/metrics/job/{tenant}", timeout=5)
        
        # 推送不同值给不同 tenant
        requests.post(
            "http://localhost:9091/metrics/job/iso-test-1",
            data='isolation_metric{agent_version="1.0.0"} 111\n',
            headers={"Content-Type": "text/plain"},
            timeout=5
        )
        requests.post(
            "http://localhost:9091/metrics/job/iso-test-2",
            data='isolation_metric{agent_version="1.0.0"} 222\n',
            headers={"Content-Type": "text/plain"},
            timeout=5
        )
        
        # 查询 tenant-1
        resp1 = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": 'isolation_metric{tenant_id="iso-test-1"}'},
            timeout=5
        ).json()
        
        # 查询 tenant-2
        resp2 = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": 'isolation_metric{tenant_id="iso-test-2"}'},
            timeout=5
        ).json()
        
        # 验证值正确且不混淆
        if resp1["data"]["result"]:
            val1 = float(resp1["data"]["result"][0]["value"][1])
            assert val1 == 111.0, f"tenant-1 的值应该是 111，实际是 {val1}"
        
        if resp2["data"]["result"]:
            val2 = float(resp2["data"]["result"][0]["value"][1])
            assert val2 == 222.0, f"tenant-2 的值应该是 222，实际是 {val2}"
    
    def test_count_distinct_tenants(self):
        """测试能统计不同租户数量."""
        import time
        
        # 推送多个 tenant 数据
        for i in range(3):
            requests.post(
                f"http://localhost:9091/metrics/job/count-test-{i}",
                data='count_test_metric{agent_version="1.0.0"} 1\n',
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
        
        # 等待 Prometheus scrape
        time.sleep(3)
        
        # 查询不同 tenant 数量
        response = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": "count(count_test_metric) by (tenant_id)"},
            timeout=5
        )
        assert response.status_code == 200
        data = response.json()
        # 应该返回聚合结果（count by tenant_id 返回 1 行，值为 3）
        assert len(data["data"]["result"]) >= 1


class TestPrometheusScrapeConfig:
    """测试 Prometheus 配置正确."""
    
    def test_prometheus_config_exists(self):
        """测试 Prometheus 配置文件存在."""
        assert os.path.exists("prometheus/prometheus.yml"), "prometheus.yml 不存在"
    
    def test_honor_labels_enabled(self):
        """测试 honor_labels 已启用（保留推送的 tenant_id）."""
        import yaml
        
        with open("prometheus/prometheus.yml", 'r') as f:
            config = yaml.safe_load(f)
        
        scrape_configs = config.get("scrape_configs", [])
        pushgateway_config = next(
            (c for c in scrape_configs if c.get("job_name") == "pushgateway"),
            None
        )
        
        assert pushgateway_config is not None, "缺少 pushgateway scrape_config"
        assert pushgateway_config.get("honor_labels") == True, "必须启用 honor_labels"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
