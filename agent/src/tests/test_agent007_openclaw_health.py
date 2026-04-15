"""AGENT-007: `agent_health` 与 OpenClaw 网关探测（M3）对齐检查"""

from pathlib import Path

from agent.src.exporter.collector import DEFAULT_OPENCLAW_GATEWAY_HEALTH_URL


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_default_gateway_health_url_matches_stack_docs():
    assert DEFAULT_OPENCLAW_GATEWAY_HEALTH_URL == "http://127.0.0.1:18789/health"


def test_metrics_protocol_documents_openclaw_agent_health():
    doc = (REPO_ROOT / "docs" / "METRICS_PROTOCOL.md").read_text(encoding="utf-8")
    assert "OpenClaw" in doc or "小龙虾" in doc
    assert "OPENCLAW_GATEWAY_HEALTH_URL" in doc
    assert "OPENCLAW_GATEWAY_HEALTH_PROBE" in doc
