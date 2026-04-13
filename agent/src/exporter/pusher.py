"""AGENT-005: 指标推送器

将 AGENT-004 采集到的 SystemMetrics 推送到平台 Pushgateway。
协议: docs/METRICS_PROTOCOL.md (PLAT-003)

功能:
- Bearer Token 认证
- 指数退避重试 (最多 5 次, 最大 60s)
- 离线缓存 (JSON Lines spool, 上限 500 条, 超 24h 丢弃, 恢复后每批 50 条)
- 批量推送上限 100 条/次
- 推送间隔 60 秒
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import threading
from pathlib import Path
from typing import List, Optional

import requests

from agent.src.exporter.collector import MetricsCollector, SystemMetrics

logger = logging.getLogger(__name__)

MAX_SPOOL_ENTRIES = 500
SPOOL_BATCH_SIZE = 50
SPOOL_TTL_SECONDS = 86400
PUSH_BATCH_LIMIT = 100
MAX_RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 60.0
DEFAULT_PUSH_INTERVAL = 60

_NON_RETRYABLE = {400, 401, 404}


def _build_payload(metrics: SystemMetrics, tenant_id: str) -> str:
    return metrics.to_prometheus(tenant_id)


def _backoff_delay(attempt: int) -> float:
    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
    return delay + random.uniform(0, 1)


class MetricsPusher:
    def __init__(
        self,
        platform_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        api_key: Optional[str] = None,
        spool_dir: Optional[Path] = None,
        push_interval: int = DEFAULT_PUSH_INTERVAL,
        collector: Optional[MetricsCollector] = None,
        https_proxy: Optional[str] = None,
    ):
        self._platform_url = (
            platform_url or os.environ.get("PLATFORM_URL", "")
        ).rstrip("/")
        self._tenant_id = tenant_id or os.environ.get("TENANT_ID", "")
        self._api_key = api_key or os.environ.get("API_KEY", "")
        self._push_interval = int(
            os.environ.get("PUSH_INTERVAL", str(push_interval))
        )
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
        return f"{self._platform_url}/metrics/job/{self._tenant_id}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "text/plain",
        }

    # ---------- public API ----------

    def push(self, metrics: SystemMetrics) -> bool:
        payload = _build_payload(metrics, self._tenant_id)
        ok = self._push_with_retry(payload)
        if not ok:
            self._spool_write(payload)
        else:
            self._flush_spool()
        return ok

    def push_loop(self, stop_event: Optional[threading.Event] = None) -> None:
        logger.info("push loop started (interval=%ds)", self._push_interval)
        while stop_event is None or not stop_event.is_set():
            try:
                metrics = self._collector.collect_all()
                self.push(metrics)
            except Exception:
                logger.exception("push loop error")
            if stop_event is not None:
                if stop_event.wait(timeout=self._push_interval):
                    break
            else:
                time.sleep(self._push_interval)

    # ---------- retry ----------

    def _push_with_retry(self, payload: str) -> bool:
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                resp = self._session.post(
                    self.push_url,
                    headers=self._headers,
                    data=payload.encode("utf-8"),
                    timeout=10,
                )
                if resp.status_code == 200:
                    return True
                if resp.status_code in _NON_RETRYABLE:
                    logger.error(
                        "non-retryable %d: %s", resp.status_code, resp.text[:200]
                    )
                    return False
                logger.warning("retryable %d (attempt %d)", resp.status_code, attempt)
            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning("network error (attempt %d): %s", attempt, exc)
            except Exception:
                logger.exception("unexpected push error")
                return False
            time.sleep(_backoff_delay(attempt))
        return False

    # ---------- spool (offline cache) ----------

    def _spool_write(self, payload: str) -> None:
        entry = {"payload": payload, "ts": time.time()}
        try:
            lines = self._spool_read_lines()
            lines.append(json.dumps(entry, ensure_ascii=False))
            if len(lines) > MAX_SPOOL_ENTRIES:
                lines = lines[-MAX_SPOOL_ENTRIES:]
            self._spool_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            logger.exception("spool write failed")

    def _spool_read_lines(self) -> List[str]:
        if not self._spool_path.exists():
            return []
        try:
            raw = self._spool_path.read_text(encoding="utf-8").strip()
            return [l for l in raw.split("\n") if l]
        except Exception:
            return []

    def _flush_spool(self) -> None:
        lines = self._spool_read_lines()
        if not lines:
            return
        now = time.time()
        remaining: List[str] = []
        batch: List[str] = []
        for raw_line in lines:
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if now - entry.get("ts", 0) > SPOOL_TTL_SECONDS:
                continue
            batch.append(entry["payload"])
            if len(batch) >= SPOOL_BATCH_SIZE:
                if not self._push_batch(batch):
                    remaining.extend(
                        json.dumps({"payload": p, "ts": entry["ts"]})
                        for p in batch
                    )
                batch = []
        if batch:
            if not self._push_batch(batch):
                remaining.extend(
                    json.dumps({"payload": p, "ts": now}) for p in batch
                )
        try:
            if remaining:
                self._spool_path.write_text(
                    "\n".join(remaining) + "\n", encoding="utf-8"
                )
            else:
                self._spool_path.unlink(missing_ok=True)
        except Exception:
            logger.exception("spool cleanup failed")

    def _push_batch(self, payloads: List[str]) -> bool:
        combined = "".join(payloads[:PUSH_BATCH_LIMIT])
        return self._push_with_retry(combined)
