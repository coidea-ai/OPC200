"""System metrics collector for OPC Agent.

Collects CPU, memory, disk usage and agent process health,
exposing them as Prometheus-compatible gauge metrics.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import psutil
from prometheus_client import Gauge, CollectorRegistry

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY = CollectorRegistry()


@dataclass(frozen=True)
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    memory_total_bytes: int
    disk_percent: float
    disk_used_bytes: int
    disk_total_bytes: int
    agent_healthy: bool
    agent_uptime_seconds: float
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects system and agent health metrics."""

    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        disk_path: str = "/",
    ):
        self._registry = registry or DEFAULT_REGISTRY
        self._disk_path = disk_path
        self._start_time = time.monotonic()

        if os.name == "nt":
            self._disk_path = "C:\\"

        self._cpu_usage = Gauge(
            "cpu_usage",
            "CPU usage percentage",
            registry=self._registry,
        )
        self._memory_usage = Gauge(
            "memory_usage",
            "Memory usage percentage",
            registry=self._registry,
        )
        self._memory_used_bytes = Gauge(
            "memory_used_bytes",
            "Memory used in bytes",
            registry=self._registry,
        )
        self._memory_total_bytes = Gauge(
            "memory_total_bytes",
            "Total memory in bytes",
            registry=self._registry,
        )
        self._disk_usage = Gauge(
            "disk_usage",
            "Disk usage percentage",
            registry=self._registry,
        )
        self._disk_used_bytes = Gauge(
            "disk_used_bytes",
            "Disk used in bytes",
            registry=self._registry,
        )
        self._disk_total_bytes = Gauge(
            "disk_total_bytes",
            "Total disk in bytes",
            registry=self._registry,
        )
        self._agent_health = Gauge(
            "agent_health",
            "Agent health status (1=healthy, 0=unhealthy)",
            registry=self._registry,
        )
        self._agent_uptime = Gauge(
            "agent_uptime_seconds",
            "Agent uptime in seconds",
            registry=self._registry,
        )

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry

    def collect(self) -> SystemMetrics:
        """Collect all metrics and update Prometheus gauges. Returns a snapshot."""
        cpu = self._collect_cpu()
        mem = self._collect_memory()
        disk = self._collect_disk()
        healthy = self._check_health()
        uptime = time.monotonic() - self._start_time

        self._cpu_usage.set(cpu)
        self._memory_usage.set(mem.percent)
        self._memory_used_bytes.set(mem.used)
        self._memory_total_bytes.set(mem.total)
        self._disk_usage.set(disk.percent)
        self._disk_used_bytes.set(disk.used)
        self._disk_total_bytes.set(disk.total)
        self._agent_health.set(1.0 if healthy else 0.0)
        self._agent_uptime.set(uptime)

        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_bytes=mem.used,
            memory_total_bytes=mem.total,
            disk_percent=disk.percent,
            disk_used_bytes=disk.used,
            disk_total_bytes=disk.total,
            agent_healthy=healthy,
            agent_uptime_seconds=uptime,
        )

    def _collect_cpu(self) -> float:
        try:
            return psutil.cpu_percent(interval=1)
        except Exception:
            logger.exception("Failed to collect CPU metrics")
            return 0.0

    def _collect_memory(self):
        try:
            return psutil.virtual_memory()
        except Exception:
            logger.exception("Failed to collect memory metrics")

            @dataclass
            class _Fallback:
                percent: float = 0.0
                used: int = 0
                total: int = 0

            return _Fallback()

    def _collect_disk(self):
        try:
            return psutil.disk_usage(self._disk_path)
        except Exception:
            logger.exception("Failed to collect disk metrics for %s", self._disk_path)

            @dataclass
            class _Fallback:
                percent: float = 0.0
                used: int = 0
                total: int = 0

            return _Fallback()

    def _check_health(self) -> bool:
        try:
            proc = psutil.Process()
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            logger.exception("Failed to check agent health")
            return False
