# AGENT-008: OpenClaw 非交互 onboard 安装脚本契约
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _ps1() -> str:
    return (SCRIPTS_DIR / "install.ps1").read_text(encoding="utf-8")


def _sh() -> str:
    return (SCRIPTS_DIR / "install.sh").read_text(encoding="utf-8")


def test_install_ps1_declares_openclaw_onboard_params():
    s = _ps1()
    assert "[switch]$OpenClawOnboard" in s
    assert "[switch]$SkipOpenClawOnboard" in s
    assert "[string]$OpenClawAuthChoice" in s


def test_install_ps1_has_non_interactive_onboard():
    s = _ps1()
    assert "Install-OpenClawOnboardIfRequested" in s
    assert "onboard" in s and "--non-interactive" in s and "--accept-risk" in s
    assert "OPENCLAW_AUTH_CHOICE" in s
    assert "OPENCLAW_ONBOARD_STRICT" in s
    assert "Test-OpenClawOnboardRequested" in s
    assert "-not $Silent" in s
    assert 'OPENCLAW_ONBOARD -eq "0"' in s


def test_install_sh_openclaw_onboard_step():
    s = _sh()
    assert "step_openclaw_onboard" in s
    assert "--openclaw-onboard" in s
    assert "--skip-openclaw-onboard" in s
    assert "onboard --non-interactive --accept-risk" in s.replace("\n", " ")
    assert "OPENCLAW_ONBOARD_STRICT" in s
    assert '[[ "${OPENCLAW_ONBOARD:-}" == "0" ]]' in s
    assert "if $SILENT; then" in s
