"""AGENT-005 单元测试: MetricsPusher"""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
import requests

from agent.src.exporter.pusher import (
    MetricsPusher,
    _build_payload,
    _backoff_delay,
    MAX_SPOOL_ENTRIES,
    SPOOL_TTL_SECONDS,
    SPOOL_BATCH_SIZE,
    MAX_RETRY_ATTEMPTS,
)
from agent.src.exporter.collector import SystemMetrics, MetricsCollector


# --------------- fixtures ---------------

@pytest.fixture
def mock_collector():
    c = MagicMock(spec=MetricsCollector)
    c.collect_all.return_value = SystemMetrics(
        cpu_usage=25.0,
        memory_usage=55.0,
        disk_usage=42.0,
        agent_health=1,
        agent_version="1.0.0",
        os="linux",
    )
    return c


@pytest.fixture
def pusher(tmp_path, mock_collector):
    return MetricsPusher(
        platform_url="http://opc200.meerkatai.cn:9091",
        tenant_id="opc-test-001",
        api_key="sk-test",
        spool_dir=tmp_path,
        push_interval=60,
        collector=mock_collector,
    )


@pytest.fixture
def spool_path(tmp_path):
    return tmp_path / "queue.jsonl"


# --------------- _build_payload ---------------

class TestBuildPayload:
    def test_uses_to_prometheus(self):
        m = SystemMetrics(cpu_usage=10.0, memory_usage=20.0, disk_usage=30.0, agent_health=1)
        payload = _build_payload(m, "t-001")
        assert 'tenant_id="t-001"' in payload
        assert "cpu_usage" in payload
        assert payload.endswith("\n")


# --------------- _backoff_delay ---------------

class TestBackoff:
    def test_increases_with_attempt(self):
        d0 = _backoff_delay(0)
        d3 = _backoff_delay(3)
        assert d0 < d3 + 2

    def test_capped_at_max(self):
        d = _backoff_delay(100)
        assert d <= 61.0


# --------------- push_url / headers ---------------

class TestPusherInit:
    def test_push_url(self, pusher):
        assert pusher.push_url == "http://opc200.meerkatai.cn:9091/metrics/job/opc-test-001"

    def test_headers(self, pusher):
        h = pusher._headers
        assert h["Authorization"] == "Bearer sk-test"
        assert h["Content-Type"] == "text/plain"


# --------------- push success ---------------

class TestPushSuccess:
    def test_push_returns_true_on_200(self, pusher, mock_collector):
        resp = MagicMock()
        resp.status_code = 200
        pusher._session.post = MagicMock(return_value=resp)

        m = mock_collector.collect_all()
        assert pusher.push(m) is True
        pusher._session.post.assert_called_once()

    def test_push_cleans_spool_on_success(self, pusher, mock_collector, spool_path):
        entry = json.dumps({"payload": "old\n", "ts": time.time()})
        pusher._spool_path.write_text(entry + "\n", encoding="utf-8")

        resp = MagicMock()
        resp.status_code = 200
        pusher._session.post = MagicMock(return_value=resp)

        pusher.push(mock_collector.collect_all())
        assert not pusher._spool_path.exists() or pusher._spool_path.read_text().strip() == ""


# --------------- push failure & spool ---------------

class TestPushFailure:
    @patch("agent.src.exporter.pusher.time.sleep")
    def test_push_spools_on_failure(self, mock_sleep, pusher, mock_collector):
        pusher._session.post = MagicMock(side_effect=requests.ConnectionError("down"))

        m = mock_collector.collect_all()
        assert pusher.push(m) is False
        assert pusher._spool_path.exists()
        lines = pusher._spool_path.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert "payload" in entry

    @patch("agent.src.exporter.pusher.time.sleep")
    def test_non_retryable_status(self, mock_sleep, pusher, mock_collector):
        resp = MagicMock()
        resp.status_code = 401
        resp.text = "Unauthorized"
        pusher._session.post = MagicMock(return_value=resp)

        m = mock_collector.collect_all()
        assert pusher.push(m) is False
        assert pusher._session.post.call_count == 1

    @patch("agent.src.exporter.pusher.time.sleep")
    def test_retryable_status_retries(self, mock_sleep, pusher, mock_collector):
        resp500 = MagicMock()
        resp500.status_code = 500
        resp500.text = "err"
        resp200 = MagicMock()
        resp200.status_code = 200
        pusher._session.post = MagicMock(side_effect=[resp500, resp200])

        m = mock_collector.collect_all()
        assert pusher.push(m) is True
        assert pusher._session.post.call_count == 2


# --------------- spool TTL ---------------

class TestSpoolTTL:
    @patch("agent.src.exporter.pusher.time.sleep")
    def test_expired_entries_discarded(self, mock_sleep, pusher):
        old_ts = time.time() - SPOOL_TTL_SECONDS - 100
        entry = json.dumps({"payload": "stale\n", "ts": old_ts})
        pusher._spool_path.write_text(entry + "\n", encoding="utf-8")

        resp = MagicMock()
        resp.status_code = 200
        pusher._session.post = MagicMock(return_value=resp)
        pusher._flush_spool()

        assert not pusher._spool_path.exists()
        pusher._session.post.assert_not_called()


# --------------- spool capacity ---------------

class TestSpoolCapacity:
    @patch("agent.src.exporter.pusher.time.sleep")
    def test_spool_capped_at_max(self, mock_sleep, pusher):
        pusher._session.post = MagicMock(side_effect=requests.ConnectionError("down"))
        now = time.time()
        lines = [
            json.dumps({"payload": f"m{i}\n", "ts": now})
            for i in range(MAX_SPOOL_ENTRIES + 10)
        ]
        pusher._spool_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        m = SystemMetrics(cpu_usage=1.0, memory_usage=2.0, disk_usage=3.0)
        pusher.push(m)
        stored = pusher._spool_path.read_text().strip().split("\n")
        assert len(stored) <= MAX_SPOOL_ENTRIES


# --------------- flush batching ---------------

class TestFlushBatching:
    @patch("agent.src.exporter.pusher.time.sleep")
    def test_flush_sends_in_batches(self, mock_sleep, pusher):
        now = time.time()
        n = SPOOL_BATCH_SIZE + 10
        lines = [
            json.dumps({"payload": f"line{i}\n", "ts": now})
            for i in range(n)
        ]
        pusher._spool_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        resp = MagicMock()
        resp.status_code = 200
        pusher._session.post = MagicMock(return_value=resp)

        pusher._flush_spool()
        assert pusher._session.post.call_count == 2


# --------------- env fallback ---------------

class TestEnvFallback:
    @patch.dict("os.environ", {
        "PLATFORM_URL": "https://env.example.com",
        "TENANT_ID": "env-tenant",
        "API_KEY": "env-key",
    })
    def test_reads_from_env(self, tmp_path):
        mc = MagicMock(spec=MetricsCollector)
        p = MetricsPusher(spool_dir=tmp_path, collector=mc)
        assert p.push_url == "https://env.example.com/metrics/job/env-tenant"
        assert p._headers["Authorization"] == "Bearer env-key"
