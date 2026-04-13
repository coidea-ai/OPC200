"""Tests for agent/src/opc_agent/config_loader.py"""

import os
from pathlib import Path

import pytest
import yaml

from agent.src.opc_agent.config_loader import (
    apply_to_environ,
    gateway_bind,
    load_agent_config,
    load_env_file,
    push_interval,
)


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    root = tmp_path / "opc200"
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True)
    data = {
        "platform": {"url": "http://127.0.0.1:9091"},
        "customer": {"id": "t-001"},
        "agent": {"version": "2.3.0", "push_interval": 45},
        "gateway": {"host": "127.0.0.1", "port": 18080},
    }
    p = cfg_dir / "config.yml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    env = root / ".env"
    env.write_text("OPC200_API_KEY=secret-key\n", encoding="utf-8")
    return p


def test_load_env_file_parses_keys(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text('API_KEY=abc\nOPC200_API_KEY=xyz\n', encoding="utf-8")
    d = load_env_file(p)
    assert d["API_KEY"] == "abc"
    assert d["OPC200_API_KEY"] == "xyz"


def test_apply_to_environ_sets_platform_tenant_api(tmp_config: Path) -> None:
    data = load_agent_config(tmp_config)
    old = {k: os.environ.get(k) for k in ("PLATFORM_URL", "TENANT_ID", "API_KEY")}
    try:
        root = apply_to_environ(tmp_config, data)
        assert root == tmp_config.resolve().parent.parent
        assert os.environ["PLATFORM_URL"] == "http://127.0.0.1:9091"
        assert os.environ["TENANT_ID"] == "t-001"
        assert os.environ["API_KEY"] == "secret-key"
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_gateway_bind_and_push_interval(tmp_config: Path) -> None:
    data = load_agent_config(tmp_config)
    assert gateway_bind(data) == ("127.0.0.1", 18080)
    assert push_interval(data) == 45


def test_apply_raises_without_platform_url(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True)
    p = cfg_dir / "config.yml"
    p.write_text(yaml.safe_dump({"customer": {"id": "x"}}), encoding="utf-8")
    data = load_agent_config(p)
    with pytest.raises(ValueError, match="platform.url"):
        apply_to_environ(p, data)
