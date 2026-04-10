"""Unit tests for agent/src/exporter/collector.py"""

from unittest.mock import patch, MagicMock
from dataclasses import dataclass

import pytest
from prometheus_client import CollectorRegistry

from agent.src.exporter.collector import MetricsCollector, SystemMetrics


@pytest.fixture
def collector():
    registry = CollectorRegistry()
    return MetricsCollector(registry=registry)


@dataclass
class FakeMemory:
    percent: float = 55.0
    used: int = 8 * 1024**3
    total: int = 16 * 1024**3


@dataclass
class FakeDisk:
    percent: float = 42.0
    used: int = 100 * 1024**3
    total: int = 256 * 1024**3


class TestMetricsCollector:
    @patch("agent.src.exporter.collector.psutil")
    def test_collect_returns_system_metrics(self, mock_psutil, collector):
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = FakeMemory()
        mock_psutil.disk_usage.return_value = FakeDisk()
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_proc.status.return_value = "running"
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.STATUS_ZOMBIE = "zombie"

        m = collector.collect()

        assert isinstance(m, SystemMetrics)
        assert m.cpu_percent == 25.0
        assert m.memory_percent == 55.0
        assert m.memory_used_bytes == 8 * 1024**3
        assert m.disk_percent == 42.0
        assert m.disk_used_bytes == 100 * 1024**3
        assert m.agent_healthy is True
        assert m.agent_uptime_seconds >= 0

    @patch("agent.src.exporter.collector.psutil")
    def test_collect_updates_prometheus_gauges(self, mock_psutil, collector):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.virtual_memory.return_value = FakeMemory(percent=30.0)
        mock_psutil.disk_usage.return_value = FakeDisk(percent=60.0)
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_proc.status.return_value = "running"
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.STATUS_ZOMBIE = "zombie"

        collector.collect()

        registry = collector.registry
        assert registry.get_sample_value("cpu_usage") == 10.0
        assert registry.get_sample_value("memory_usage") == 30.0
        assert registry.get_sample_value("disk_usage") == 60.0
        assert registry.get_sample_value("agent_health") == 1.0

    @patch("agent.src.exporter.collector.psutil")
    def test_unhealthy_when_zombie(self, mock_psutil, collector):
        mock_psutil.cpu_percent.return_value = 0.0
        mock_psutil.virtual_memory.return_value = FakeMemory()
        mock_psutil.disk_usage.return_value = FakeDisk()
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_proc.status.return_value = "zombie"
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.STATUS_ZOMBIE = "zombie"

        m = collector.collect()

        assert m.agent_healthy is False
        assert collector.registry.get_sample_value("agent_health") == 0.0

    @patch("agent.src.exporter.collector.psutil")
    def test_cpu_exception_returns_zero(self, mock_psutil, collector):
        mock_psutil.cpu_percent.side_effect = RuntimeError("no cpu info")
        mock_psutil.virtual_memory.return_value = FakeMemory()
        mock_psutil.disk_usage.return_value = FakeDisk()
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_proc.status.return_value = "running"
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.STATUS_ZOMBIE = "zombie"

        m = collector.collect()

        assert m.cpu_percent == 0.0

    @patch("agent.src.exporter.collector.psutil")
    def test_disk_exception_returns_zero(self, mock_psutil, collector):
        mock_psutil.cpu_percent.return_value = 5.0
        mock_psutil.virtual_memory.return_value = FakeMemory()
        mock_psutil.disk_usage.side_effect = OSError("disk not found")
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_proc.status.return_value = "running"
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.STATUS_ZOMBIE = "zombie"

        m = collector.collect()

        assert m.disk_percent == 0.0
        assert m.disk_used_bytes == 0

    @patch("agent.src.exporter.collector.psutil")
    def test_health_check_exception_returns_false(self, mock_psutil, collector):
        mock_psutil.cpu_percent.return_value = 1.0
        mock_psutil.virtual_memory.return_value = FakeMemory()
        mock_psutil.disk_usage.return_value = FakeDisk()
        mock_psutil.Process.side_effect = RuntimeError("no process")

        m = collector.collect()

        assert m.agent_healthy is False
