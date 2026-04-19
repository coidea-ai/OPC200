"""AGENT-009: opc200-install.sh 与 Release 行为一致的最小契约检查。"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SH = ROOT / "agent" / "scripts" / "opc200-install.sh"


@pytest.fixture
def opc200_install_sh() -> str:
    assert SH.is_file()
    return SH.read_text(encoding="utf-8")


def test_script_exists_lf_only():
    raw = SH.read_bytes()
    assert b"\r" not in raw


@pytest.mark.parametrize(
    "needle",
    [
        "OPC200_GITHUB_REPO",
        "SHA256SUMS",
        "verify_sha256sums",
        "parse_latest_release_tsv",
        "--repo-root",
        "install.sh",
        "E004=4",
        "extract_zip",
    ],
)
def test_bootstrap_contract(opc200_install_sh, needle):
    assert needle in opc200_install_sh
