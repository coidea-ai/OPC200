"""Metrics pusher for OPC Agent.

Pushes collected metrics to the platform Pushgateway using
Prometheus text format with Bearer Token authentication.

Protocol: docs/METRICS_PROTOCOL.md (PLAT-003)
"""

from __future__ import annotations

import json
import logging
import os
import platform
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import requests

from agent.src.exporter.collector import MetricsCollector, SystemMetrics

logger = logging.getLogger(__name__)

AGENT_VERSION = "0.1.0"
MAX_SPOOL_ENTRIES = 500
SPOOL_BATCH_SIZE = 50
PUSH_BATCH_SIZE = 100
SPOOL_TTL_SECONDS = 86400  # 24h
MAX_RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 60.0

_NON_RETRYABLE_STATUS = {400, 401, 404}


@dataclass
class SpoolEntry:
    payload: str
    timestamp: float


def _get_os() -> str:
    s = sys.platform
    if s.startswith("win"):
        return "windows"
    if s.startswith("darwin"):
        return "darwin"
    return "linux"


def _build_payload(metrics: SystemMetrics) -> str:
    os_name = _get_os()
    labels = f'agent_version="{AGENT_VERSION}",os="{os_name}"'
    lines = [
        f'agent_health{{{labels}}} {1 if metrics.agent_healthy else 0}',
        f'cpu_usage{{{labels}}} {metrics.cpu_percent}',
        f'memory_usage{{{labels}}} {metrics.memory_percent}',
        f'disk_usage{{{labels}}} {metrics.disk_percent}',
    ]
    return "\n".join(lines) + "\n"


class MetricsPusher:
    """Pushes system metrics to the platform Pushgateway."""

    def __init__(
        self,
        platform_url: Optional[str] = None,
        customer_id: Optional[str] = None,
        api_key: Optional[str] = None,
        spool_dir: Optional[Path] = None,
        push_interval: int = 60,
        collector: Optional[MetricsCollector] = None,
        https_proxy: Optional[str] = None,
    ):
        self._platform_url = (platform_url or os.environ.get("PLATFORM_URL", "")).rstrip("/")
        self._customer_id = customer_id or os.environ.get("CUSTOMER_ID", "")
        self._api_key = api_key or os.environ.get("API_KEY", "")
        self._push_interval = int(os.environ.get("PUSH_INTERVAL", push_interval))
        self._collector = collector or MetricsCollector()
        self._https_proxy = https_proxy or os.environ.get("HTTPS_PROXY")

        if spool_dir is None:
            base = Path.home() / ".opc200" / "spool"
        else:
            base = spool_dir
        base.mkdir(parents=True, exist_ok=True)
        self._spool_path = base / "queue.jsonl"

        self._session = requests.Session()
        if self._https_proxy:
            self._session.proxies = {"https": self._https_proxy}

    @property
    def push_url(self) -> str:
        return f"{self._platform_url}/metrics/job/{self._customer_id}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "text/plain",
        }

    def push(self, metrics: SystemMetrics) -> bool:
        """Push a single metrics snapshot. Returns True on success."""
        payload = _build_payload(metrics)
        success = self._push_with_retry(payload)
        if not success:
            self._spool(payload)
        else:
            self._flush_spool()
        return success

    def push_loop(self) -> None:
        """Blocking push loop. Collects and pushes every push_interval seconds."""
        logger.info("Starting push loop (interval=%ds)", self._push_interval)
        while True:
            try:
                metrics = self._collector.collect()
                self.push(metrics)
            except Exception:
                logger.exception("Unexpected error in push loop")
            time.sleep(self._push_interval)

    def _push_with_retry(self, payload: str) -> bool:
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                resp = self._session.post(
                    self.push_url,
                    headers=self._headers,
                    data=payload,
                    timeout=10,
                )
                if resp.status_code in _NON_RETRYABLE_STATUS:
                    logger.error("Non-retryable error %d pushing metrics", resp.status_code)
                    return False
                resp.raise_for_status()
                logger.debug("Metrics pushed successfully")
                return True
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code in _NON_RETRYABLE_STATUS:
                    logger.error("Non-retryable HTTP error: %s", e)
                    return False
                delay = self._backoff_delay(attempt)
                logger.warning("Push failed (attempt %d/%d), retrying in %.1fs: %s", attempt + 1, MAX_RETRY_ATTEMPTS, delay, e)
                time.sleep(delay)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                delay = self._backoff_delay(attempt)
                logger.warning("Push failed (attempt %d/%d), retrying in %.1fs: %s", attempt + 1, MAX_RETRY_ATTEMPTS, delay, e)
                time.sleep(delay)
        logger.error("All %d push attempts failed", MAX_RETRY_ATTEMPTS)
        return False

    def _backoff_delay(self, attempt: int) -> float:
        delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
        jitter = random.uniform(0, 1)
        return delay + jitter

    def _spool(self, payload: str) -> None:
        entries = self._load_spool()
        entries.append(SpoolEntry(payload=payload, timestamp=time.time()))
        if len(entries) > MAX_SPOOL_ENTRIES:
            entries = entries[-MAX_SPOOL_ENTRIES:]
        self._save_spool(entries)
        logger.debug("Spooled metrics (total=%d)", len(entries))

    def _flush_spool(self) -> None:
        entries = self._load_spool()
        if not entries:
            return

        now = time.time()
        entries = [e for e in entries if now - e.timestamp < SPOOL_TTL_SECONDS]
        if not entries:
            self._save_spool([])
            return

        logger.info("Flushing %d spooled entries", len(entries))
        remaining: List[SpoolEntry] = []

        for i in range(0, len(entries), SPOOL_BATCH_SIZE):
            batch = entries[i : i + SPOOL_BATCH_SIZE]
            combined = "".join(e.payload for e in batch)
            if not self._push_with_retry(combined):
                remaining.extend(entries[i:])
                break

        self._save_spool(remaining)

    def _load_spool(self) -> List[SpoolEntry]:
        if not self._spool_path.exists():
            return []
        entries: List[SpoolEntry] = []
        try:
            for line in self._spool_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    d = json.loads(line)
                    entries.append(SpoolEntry(**d))
        except Exception:
            logger.exception("Failed to load spool, resetting")
            self._spool_path.unlink(missing_ok=True)
        return entries

    def _save_spool(self, entries: List[SpoolEntry]) -> None:
        try:
            content = "\n".join(json.dumps(asdict(e)) for e in entries)
            self._spool_path.write_text(content + "\n" if content else "", encoding="utf-8")
        except Exception:
            logger.exception("Failed to save spool")
