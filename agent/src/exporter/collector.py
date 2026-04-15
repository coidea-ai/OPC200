"""AGENT-004: 系统指标采集器

使用 psutil 跨平台采集 CPU / 内存 / 磁盘使用率及指标 `agent_health`。

`agent_health` 语义（AGENT-007 / 预装小龙虾）：表示 **OpenClaw（小龙虾）网关侧可观测健康**，
默认探测 `OPENCLAW_GATEWAY_HEALTH_URL`（与安装脚本约定目录及文档 `18789` 网关一致），
并结合本进程（opc-agent / exporter 所在进程）非僵尸存活检查。

环境变量（单一配置源，与安装脚本 `OPENCLAW_PROFILE_DIR` 命名对齐）：

- `OPENCLAW_GATEWAY_HEALTH_URL`：网关 HTTP 健康 URL，默认 `http://127.0.0.1:18789/health`
- `OPENCLAW_GATEWAY_HEALTH_PROBE`：设为 `0`/`false`/`off` 时跳过网关探测（仅进程存活则报 1，供无 OpenClaw 环境）
"""

from __future__ import annotations

import os
import platform
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

REQUIRED_LABELS = ("tenant_id", "agent_version", "os")
OPTIONAL_LABELS = ("arch", "hostname")
METRIC_NAMES = ("agent_health", "cpu_usage", "memory_usage", "disk_usage")

DEFAULT_OPENCLAW_GATEWAY_HEALTH_URL = "http://127.0.0.1:18789/health"


def _openclaw_gateway_health_url() -> str:
    return os.environ.get("OPENCLAW_GATEWAY_HEALTH_URL", DEFAULT_OPENCLAW_GATEWAY_HEALTH_URL).strip()


def _openclaw_gateway_probe_enabled() -> bool:
    v = os.environ.get("OPENCLAW_GATEWAY_HEALTH_PROBE", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def probe_openclaw_gateway_health(url: Optional[str] = None, timeout_sec: float = 3.0) -> bool:
    """对 OpenClaw 网关发起 HTTP GET；2xx 视为健康。供单测 mock / 直接调用。"""
    u = (url or _openclaw_gateway_health_url()).strip()
    if not u:
        return True
    req = urllib.request.Request(u)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            return 200 <= int(code) < 300
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return False


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
            health = self._compute_agent_health()
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

    def _compute_agent_health(self) -> int:
        if not self._process_running_ok():
            return 0
        if _openclaw_gateway_probe_enabled():
            if not probe_openclaw_gateway_health():
                return 0
        return 1

    @staticmethod
    def _process_running_ok() -> int:
        try:
            proc = psutil.Process(os.getpid())
            if not proc.is_running():
                return 0
            if proc.status() == psutil.STATUS_ZOMBIE:
                return 0
        except Exception:
            return 0
        return 1
