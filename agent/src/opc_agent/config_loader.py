"""Load install.ps1 / install.sh style config.yml and ~/.opc200/.env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_agent_config(config_path: Path) -> Dict[str, Any]:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("config.yml must be a mapping")
    return raw


def apply_to_environ(
    config_path: Path,
    data: Dict[str, Any],
) -> Path:
    """Set PLATFORM_URL, TENANT_ID, API_KEY for MetricsPusher. Returns install root."""
    install_root = config_path.resolve().parent.parent
    env_path = install_root / ".env"
    env_file = load_env_file(env_path)

    platform = data.get("platform") or {}
    customer = data.get("customer") or {}

    url = (platform.get("url") or "").strip().rstrip("/")
    if not url:
        raise ValueError("platform.url is required in config.yml")
    os.environ["PLATFORM_URL"] = url

    cid = (customer.get("id") or "").strip()
    if not cid:
        raise ValueError("customer.id is required in config.yml")
    os.environ["TENANT_ID"] = cid

    key = env_file.get("API_KEY") or env_file.get("OPC200_API_KEY")
    if key:
        os.environ["API_KEY"] = key
    elif not os.environ.get("API_KEY"):
        os.environ["API_KEY"] = "unset"

    return install_root


def gateway_bind(cfg: Dict[str, Any]) -> tuple[str, int]:
    gw = cfg.get("gateway") or {}
    host = str(gw.get("host") or "127.0.0.1")
    port = int(gw.get("port") or 8080)
    return host, port


def agent_version(cfg: Dict[str, Any]) -> str:
    ag = cfg.get("agent") or {}
    return str(ag.get("version") or "2.3.0")


def push_interval(cfg: Dict[str, Any]) -> int:
    ag = cfg.get("agent") or {}
    return int(ag.get("push_interval") or 60)
