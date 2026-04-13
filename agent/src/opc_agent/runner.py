"""HTTP /health + metrics push loop (used by CLI and Windows service)."""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from agent.src.exporter.collector import MetricsCollector
from agent.src.exporter.pusher import MetricsPusher
from agent.src.opc_agent.config_loader import (
    agent_version,
    apply_to_environ,
    gateway_bind,
    load_agent_config,
    push_interval,
)

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health" or self.path.startswith("/health?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        logger.debug("%s - %s", self.address_string(), fmt % args)


def parse_config_arg(argv: list[str]) -> Optional[Path]:
    for i, a in enumerate(argv):
        if a == "--config" and i + 1 < len(argv):
            return Path(argv[i + 1])
    return None


def argv_tail(argv: list[str]) -> list[str]:
    """Argv tokens after stripping --config and its value (excludes program name)."""
    out: list[str] = []
    i = 1
    while i < len(argv):
        if argv[i] == "--config" and i + 1 < len(argv):
            i += 2
            continue
        out.append(argv[i])
        i += 1
    return out


def run_agent(
    config_path: Path,
    stop_event: threading.Event,
    *,
    log_file: Optional[Path] = None,
) -> None:
    """Start /health server and metrics push; return when stop_event is set."""
    if log_file:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            filename=str(log_file),
            encoding="utf-8",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    data = load_agent_config(config_path)
    install_root = apply_to_environ(config_path, data)
    host, port = gateway_bind(data)
    ver = agent_version(data)
    interval = push_interval(data)

    spool_dir = install_root / "spool"
    spool_dir.mkdir(parents=True, exist_ok=True)

    collector = MetricsCollector(agent_version=ver)
    pusher = MetricsPusher(
        spool_dir=spool_dir,
        push_interval=interval,
        collector=collector,
    )

    server = ThreadingHTTPServer((host, port), _HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info("health server listening on http://%s:%s/health", host, port)

    push_thread = threading.Thread(
        target=lambda: pusher.push_loop(stop_event),
        daemon=True,
    )
    push_thread.start()

    stop_event.wait()
    logger.info("shutting down")
    server.shutdown()
    server.server_close()
    push_thread.join(timeout=30)


