"""AGENT-004 单元测试: MetricsCollector & SystemMetrics"""

from unittest.mock import patch, MagicMock
from dataclasses import dataclass

import pytest

from agent.src.exporter.collector import (
    MetricsCollector,
    SystemMetrics,
    _detect_os,
    METRIC_NAMES,
    REQUIRED_LABELS,
)


# --------------- fixtures ---------------

@dataclass
class _FakeMem:
    percent: float = 55.0


@dataclass
class _FakeDisk:
    percent: float = 42.0


@pytest.fixture
def collector():
    with patch("agent.src.exporter.collector.psutil") as mock_ps:
        mock_ps.cpu_percent.return_value = 25.0
        mock_ps.virtual_memory.return_value = _FakeMem()
        mock_ps.disk_usage.return_value = _FakeDisk()
        proc = MagicMock()
        proc.is_running.return_value = True
        proc.status.return_value = "running"
        mock_ps.Process.return_value = proc
        mock_ps.STATUS_ZOMBIE = "zombie"
        c = MetricsCollector.__new__(MetricsCollector)
        c.agent_version = "1.0.0"
        c.os = "linux"
        c.arch = "x86_64"
        c.hostname = "test-host"
        c._boot_time = 0
        yield c, mock_ps


# --------------- SystemMetrics ---------------

class TestSystemMetrics:
    def test_default_values(self):
        m = SystemMetrics()
        assert m.cpu_usage == 0.0
        assert m.memory_usage == 0.0
        assert m.disk_usage == 0.0
        assert m.agent_health == 1
        assert m.error is None

    def test_to_prometheus_format(self):
        m = SystemMetrics(
            cpu_usage=45.5,
            memory_usage=78.2,
            disk_usage=65.0,
            agent_health=1,
            agent_version="1.0.0",
            os="linux",
        )
        output = m.to_prometheus("opc-001")
        lines = output.strip().split("\n")
        assert len(lines) == 4

        for name in METRIC_NAMES:
            assert any(name in l for l in lines)

        for label in REQUIRED_LABELS:
            assert label in output

        assert 'tenant_id="opc-001"' in output
        assert 'agent_version="1.0.0"' in output
        assert 'os="linux"' in output
        assert "45.5" in output

    def test_to_prometheus_ends_with_newline(self):
        m = SystemMetrics()
        assert m.to_prometheus("t").endswith("\n")

    def test_to_dict(self):
        m = SystemMetrics(cpu_usage=50.0, memory_usage=60.0, disk_usage=70.0, agent_health=1)
        d = m.to_dict()
        assert d == {
            "agent_health": 1,
            "cpu_usage": 50.0,
            "memory_usage": 60.0,
            "disk_usage": 70.0,
        }


# --------------- MetricsCollector ---------------

class TestCollector:
    def test_collect_all_returns_system_metrics(self, collector):
        c, mock_ps = collector
        m = c.collect_all()
        assert isinstance(m, SystemMetrics)
        assert m.cpu_usage == 25.0
        assert m.memory_usage == 55.0
        assert m.disk_usage == 42.0
        assert m.agent_health == 1
        assert m.agent_version == "1.0.0"
        assert m.os == "linux"

    def test_cpu_exception_returns_zero(self, collector):
        c, mock_ps = collector
        mock_ps.cpu_percent.side_effect = RuntimeError("boom")
        assert c._collect_cpu() == 0.0

    def test_memory_exception_returns_zero(self, collector):
        c, mock_ps = collector
        mock_ps.virtual_memory.side_effect = RuntimeError("boom")
        assert c._collect_memory() == 0.0

    def test_disk_exception_returns_zero(self, collector):
        c, mock_ps = collector
        mock_ps.disk_usage.side_effect = OSError("no disk")
        assert c._collect_disk() == 0.0

    def test_health_zombie_returns_zero(self, collector):
        c, mock_ps = collector
        proc = MagicMock()
        proc.is_running.return_value = True
        proc.status.return_value = "zombie"
        mock_ps.Process.return_value = proc
        assert c._check_health(10.0, 20.0, 30.0) == 0

    def test_health_all_zero_returns_zero(self, collector):
        c, _ = collector
        assert c._check_health(0.0, 0.0, 0.0) == 0

    def test_health_process_exception_returns_zero(self, collector):
        c, mock_ps = collector
        mock_ps.Process.side_effect = RuntimeError("no proc")
        assert c._check_health(10.0, 20.0, 30.0) == 0

    def test_collect_all_error_fallback(self, collector):
        c, mock_ps = collector
        mock_ps.cpu_percent.side_effect = RuntimeError("fatal")
        mock_ps.virtual_memory.side_effect = RuntimeError("fatal")
        mock_ps.disk_usage.side_effect = RuntimeError("fatal")
        proc = MagicMock()
        proc.is_running.return_value = True
        proc.status.return_value = "running"
        mock_ps.Process.return_value = proc
        m = c.collect_all()
        assert m.agent_health == 0

    def test_psutil_not_installed(self):
        with patch("agent.src.exporter.collector.psutil", None):
            with pytest.raises(RuntimeError, match="psutil is required"):
                MetricsCollector()


class TestDetectOS:
    @patch("agent.src.exporter.collector.platform")
    def test_linux(self, mock_plat):
        mock_plat.system.return_value = "Linux"
        assert _detect_os() == "linux"

    @patch("agent.src.exporter.collector.platform")
    def test_darwin(self, mock_plat):
        mock_plat.system.return_value = "Darwin"
        assert _detect_os() == "darwin"

    @patch("agent.src.exporter.collector.platform")
    def test_windows(self, mock_plat):
        mock_plat.system.return_value = "Windows"
        assert _detect_os() == "windows"
