"""AGENT-004: 系统指标采集器

使用 psutil 跨平台采集 CPU / 内存 / 磁盘使用率及 Agent 健康状态，
输出符合 PLAT-003 协议的 Prometheus text format。
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

REQUIRED_LABELS = ("tenant_id", "agent_version", "os")
OPTIONAL_LABELS = ("arch", "hostname")
METRIC_NAMES = ("agent_health", "cpu_usage", "memory_usage", "disk_usage")


def _detect_os() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "darwin"
    if s == "windows":
        return "windows"
    return "linux"


@dataclass
class SystemMetrics:
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    agent_health: int = 1
    agent_version: str = "1.0.0"
    os: str = field(default_factory=_detect_os)
    arch: str = field(default_factory=lambda: platform.machine().lower())
    hostname: str = field(default_factory=platform.node)
    error: Optional[str] = None

    def to_prometheus(self, tenant_id: str) -> str:
        required = (
            f'tenant_id="{tenant_id}",'
            f'agent_version="{self.agent_version}",'
            f'os="{self.os}"'
        )
        lines = [
            f"agent_health{{{required}}} {self.agent_health}",
            f"cpu_usage{{{required}}} {self.cpu_usage:.1f}",
            f"memory_usage{{{required}}} {self.memory_usage:.1f}",
            f"disk_usage{{{required}}} {self.disk_usage:.1f}",
        ]
        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        return {
            "agent_health": self.agent_health,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
        }


class MetricsCollector:
    def __init__(self, agent_version: str = "1.0.0"):
        if psutil is None:
            raise RuntimeError("psutil is required: pip install psutil")
        self.agent_version = agent_version
        self.os = _detect_os()
        self.arch = platform.machine().lower()
        self.hostname = platform.node()
        self._boot_time = time.monotonic()

    def collect_all(self) -> SystemMetrics:
        try:
            cpu = self._collect_cpu()
            mem = self._collect_memory()
            disk = self._collect_disk()
            health = self._check_health(cpu, mem, disk)
            return SystemMetrics(
                cpu_usage=cpu,
                memory_usage=mem,
                disk_usage=disk,
                agent_health=health,
                agent_version=self.agent_version,
                os=self.os,
                arch=self.arch,
                hostname=self.hostname,
            )
        except Exception as e:
            return SystemMetrics(
                agent_version=self.agent_version,
                os=self.os,
                arch=self.arch,
                hostname=self.hostname,
                agent_health=0,
                error=str(e),
            )

    def _collect_cpu(self) -> float:
        try:
            val = psutil.cpu_percent(interval=1)
            return round(float(val), 1)
        except Exception:
            return 0.0

    def _collect_memory(self) -> float:
        try:
            mem = psutil.virtual_memory()
            return round(float(mem.percent), 1)
        except Exception:
            return 0.0

    def _collect_disk(self) -> float:
        try:
            root = "C:\\" if self.os == "windows" else "/"
            disk = psutil.disk_usage(root)
            return round(float(disk.percent), 1)
        except Exception:
            return 0.0

    @staticmethod
    def _check_health(cpu: float, mem: float, disk: float) -> int:
        try:
            proc = psutil.Process(os.getpid())
            if not proc.is_running():
                return 0
            if proc.status() == psutil.STATUS_ZOMBIE:
                return 0
        except Exception:
            return 0
        if cpu == 0.0 and mem == 0.0 and disk == 0.0:
            return 0
        return 1
