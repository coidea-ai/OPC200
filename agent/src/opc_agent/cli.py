"""opc-agent CLI: --config PATH (run | service run) — 本地健康检查 + 指标推送。

install.ps1 注册的 Windows 服务若出现 1053，说明 SCM 需要原生 Service 宿主；
联调阶段可前台运行: opc-agent.exe --config ... run
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path

from agent.src.opc_agent.runner import argv_tail, parse_config_arg, run_agent


def main() -> None:
    cfg = parse_config_arg(sys.argv)
    if not cfg:
        sys.stderr.write(
            "usage: opc-agent --config PATH (run | service run)\n"
            "  run          — 前台运行（联调 / LocalBinary 推荐）\n"
            "  service run  — 与 run 相同（保留与 install.ps1 参数一致）\n"
        )
        sys.exit(2)

    tail = argv_tail(sys.argv)
    if tail == ["run"] or tail == ["service", "run"]:
        pass
    else:
        sys.stderr.write(
            "expected trailing: run   OR   service run\n"
            f"got: {tail!r}\n"
        )
        sys.exit(2)

    log_path = cfg.resolve().parent.parent / "logs" / "agent.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()

    def _stop(*_: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    run_agent(cfg, stop, log_file=log_path)


if __name__ == "__main__":
    main()
