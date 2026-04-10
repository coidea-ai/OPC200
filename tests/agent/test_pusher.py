"""Unit tests for agent/src/exporter/pusher.py"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from prometheus_client import CollectorRegistry

from agent.src.exporter.collector import MetricsCollector, SystemMetrics
from agent.src.exporter.pusher import (
    MAX_SPOOL_ENTRIES,
    SPOOL_TTL_SECONDS,
    MetricsPusher,
    SpoolEntry,
    _build_payload,
    _get_os,
)


@pytest.fixture
def spool_dir(tmp_path):
    return tmp_path / "spool"


@pytest.fixture
def pusher(spool_dir):
    collector = MetricsCollector(registry=CollectorRegistry())
    return MetricsPusher(
        platform_url="https://platform.opc200.co",
        customer_id="opc-test",
        api_key="sk-test",
        spool_dir=spool_dir,
        collector=collector,
    )


@pytest.fixture
def healthy_metrics():
    return SystemMetrics(
        cpu_percent=25.0,
        memory_percent=50.0,
        memory_used_bytes=8 * 1024**3,
        memory_total_bytes=16 * 1024**3,
        disk_percent=40.0,
        disk_used_bytes=100 * 1024**3,
        disk_total_bytes=256 * 1024**3,
        agent_healthy=True,
        agent_uptime_seconds=100.0,
    )


class TestBuildPayload:
    def test_contains_all_metrics(self, healthy_metrics):
        payload = _build_payload(healthy_metrics)
        assert "agent_health" in payload
        assert "cpu_usage" in payload
        assert "memory_usage" in payload
        assert "disk_usage" in payload

    def test_contains_required_labels(self, healthy_metrics):
        payload = _build_payload(healthy_metrics)
        assert "agent_version=" in payload
        assert "os=" in payload

    def test_ends_with_newline(self, healthy_metrics):
        payload = _build_payload(healthy_metrics)
        assert payload.endswith("\n")

    def test_unhealthy_agent_sets_zero(self):
        m = SystemMetrics(
            cpu_percent=0.0, memory_percent=0.0,
            memory_used_bytes=0, memory_total_bytes=0,
            disk_percent=0.0, disk_used_bytes=0, disk_total_bytes=0,
            agent_healthy=False, agent_uptime_seconds=0.0,
        )
        payload = _build_payload(m)
        assert "agent_health" in payload
        assert "} 0" in payload


class TestMetricsPusher:
    def test_push_url(self, pusher):
        assert pusher.push_url == "https://platform.opc200.co/metrics/job/opc-test"

    def test_headers_use_bearer_token(self, pusher):
        assert pusher._headers["Authorization"] == "Bearer sk-test"
        assert pusher._headers["Content-Type"] == "text/plain"

    @patch("agent.src.exporter.pusher.requests.Session.post")
    def test_push_success(self, mock_post, pusher, healthy_metrics):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = pusher.push(healthy_metrics)

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "Authorization" in call_kwargs.kwargs["headers"]

    @patch("agent.src.exporter.pusher.time.sleep")
    @patch("agent.src.exporter.pusher.requests.Session.post")
    def test_push_failure_spools_metrics(self, mock_post, mock_sleep, pusher, healthy_metrics, spool_dir):
        mock_post.side_effect = requests.exceptions.ConnectionError("no network")

        result = pusher.push(healthy_metrics)

        assert result is False
        spool_file = spool_dir / "queue.jsonl"
        assert spool_file.exists()
        entries = [json.loads(l) for l in spool_file.read_text().splitlines() if l.strip()]
        assert len(entries) == 1
        assert "cpu_usage" in entries[0]["payload"]

    @patch("agent.src.exporter.pusher.time.sleep")
    @patch("agent.src.exporter.pusher.requests.Session.post")
    def test_non_retryable_401_no_retry(self, mock_post, mock_sleep, pusher, healthy_metrics):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        result = pusher._push_with_retry(_build_payload(healthy_metrics))

        assert result is False
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()

    @patch("agent.src.exporter.pusher.time.sleep")
    @patch("agent.src.exporter.pusher.requests.Session.post")
    def test_retries_on_500(self, mock_post, mock_sleep, pusher, healthy_metrics):
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 500
        mock_resp_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp_fail)

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.raise_for_status.return_value = None

        mock_post.side_effect = [mock_resp_fail, mock_resp_fail, mock_resp_ok]

        result = pusher._push_with_retry(_build_payload(healthy_metrics))

        assert result is True
        assert mock_post.call_count == 3


class TestSpool:
    def test_spool_and_load(self, pusher, spool_dir):
        pusher._spool("test_metric 1\n")
        entries = pusher._load_spool()
        assert len(entries) == 1
        assert entries[0].payload == "test_metric 1\n"

    def test_spool_trims_oldest_when_full(self, pusher):
        for i in range(MAX_SPOOL_ENTRIES + 10):
            pusher._spool(f"metric_{i} {i}\n")
        entries = pusher._load_spool()
        assert len(entries) == MAX_SPOOL_ENTRIES
        assert f"metric_{MAX_SPOOL_ENTRIES + 9}" in entries[-1].payload

    def test_flush_spool_removes_expired(self, pusher, spool_dir):
        old_entry = SpoolEntry(payload="old_metric 1\n", timestamp=time.time() - SPOOL_TTL_SECONDS - 1)
        pusher._save_spool([old_entry])

        with patch.object(pusher, "_push_with_retry", return_value=True):
            pusher._flush_spool()

        assert pusher._load_spool() == []

    @patch("agent.src.exporter.pusher.time.sleep")
    @patch("agent.src.exporter.pusher.requests.Session.post")
    def test_flush_spool_on_successful_push(self, mock_post, mock_sleep, pusher, healthy_metrics):
        pusher._spool("cached_metric 1\n")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        pusher.push(healthy_metrics)

        assert pusher._load_spool() == []
