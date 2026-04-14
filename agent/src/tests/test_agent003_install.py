"""AGENT-003 单元测试: Mac/Linux 安装/卸载脚本与 AGENT-001 规范一致性检查"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "agent" / "scripts"
SPEC_PATH = REPO_ROOT / "docs" / "INSTALL_SCRIPT_SPEC.md"


@pytest.fixture(scope="module")
def install_sh():
    return (SCRIPTS_DIR / "install.sh").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def uninstall_sh():
    return (SCRIPTS_DIR / "uninstall.sh").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec_md():
    return SPEC_PATH.read_text(encoding="utf-8")


# ── 文件存在性 ────────────────────────────────────────────────────

class TestFilesExist:
    def test_install_script_exists(self):
        assert (SCRIPTS_DIR / "install.sh").is_file()

    def test_uninstall_script_exists(self):
        assert (SCRIPTS_DIR / "uninstall.sh").is_file()

    def test_spec_exists(self):
        assert SPEC_PATH.is_file()

    def test_install_has_shebang(self, install_sh):
        assert install_sh.startswith("#!/usr/bin/env bash")

    def test_uninstall_has_shebang(self, uninstall_sh):
        assert uninstall_sh.startswith("#!/usr/bin/env bash")


# ── install.sh CLI 参数 ──────────────────────────────────────────

class TestInstallParams:
    REQUIRED_PARAMS = [
        "--platform-url", "--customer-id", "--api-key",
        "--install-dir", "--port", "--silent",
        "--local-binary", "--repo-root", "--binary", "--full-runtime-deps",
    ]

    @pytest.mark.parametrize("param", REQUIRED_PARAMS)
    def test_param_handled(self, install_sh, param):
        assert param in install_sh

    def test_set_euo_pipefail(self, install_sh):
        assert "set -euo pipefail" in install_sh


# ── 7 步流程 ─────────────────────────────────────────────────────

class TestInstallSteps:
    STEP_FUNCTIONS = [
        "step_check_env",
        "step_get_config",
        "step_install_openclaw_official",
        "step_download",
        "step_install",
        "step_register_service",
        "step_start_verify",
        "step_summary",
    ]

    @pytest.mark.parametrize("func", STEP_FUNCTIONS)
    def test_step_function_defined(self, install_sh, func):
        assert f"{func}()" in install_sh

    def test_main_calls_all_steps(self, install_sh):
        main_match = re.search(r"main\(\)\s*\{(.*?)^}", install_sh, re.DOTALL | re.MULTILINE)
        assert main_match, "未找到 main 函数"
        main_body = main_match.group(1)
        for func in self.STEP_FUNCTIONS:
            assert func in main_body


# ── 错误码 (AGENT-001 §6.1) ─────────────────────────────────────

class TestErrorCodes:
    CODES = ["E001", "E002", "E003", "E004", "E005"]

    @pytest.mark.parametrize("code", CODES)
    def test_error_code_present(self, install_sh, code):
        assert code in install_sh


# ── 目录结构 (AGENT-001 §3.1) ───────────────────────────────────

class TestDirectoryStructure:
    SPEC_DIRS = ["bin", "config", "data", "journal", "exporter", "logs"]

    @pytest.mark.parametrize("d", SPEC_DIRS)
    def test_dir_in_script(self, install_sh, d):
        assert d in install_sh

    def test_default_install_dir(self, install_sh):
        assert ".opc200" in install_sh


# ── config.yml 模板 ──────────────────────────────────────────────

class TestConfigTemplate:
    def _extract_yaml_block(self, sh_text: str) -> str:
        match = re.search(
            r'cat\s*>\s*"\$root/config/config\.yml"\s*<<YAML\n(.*?)\nYAML',
            sh_text,
            re.DOTALL,
        )
        assert match, "未找到 config.yml heredoc"
        return match.group(1).strip()

    def test_yaml_parseable(self, install_sh):
        raw = self._extract_yaml_block(install_sh)
        raw = re.sub(r'\$\{[^}]+\}', 'placeholder', raw)
        cfg = yaml.safe_load(raw)
        assert cfg is not None

    def test_contains_required_sections(self, install_sh):
        raw = self._extract_yaml_block(install_sh)
        for section in ("platform:", "customer:", "agent:", "gateway:", "journal:", "logging:"):
            assert section in raw


# ── .env 与安全 ──────────────────────────────────────────────────

class TestSecurity:
    def test_env_file_written(self, install_sh):
        assert ".env" in install_sh

    def test_chmod_600(self, install_sh):
        assert "chmod 600" in install_sh

    def test_api_key_read_silent(self, install_sh):
        assert "read -rsp" in install_sh


# ── SHA256 校验 ──────────────────────────────────────────────────

class TestChecksum:
    def test_sha256_check(self, install_sh):
        assert "sha256sum" in install_sh or "shasum" in install_sh

    def test_sha256sums_file(self, install_sh):
        assert "SHA256SUMS" in install_sh


class TestOpenClawOfficialInstall:
    def test_official_install_url_configurable(self, install_sh):
        assert "OPENCLAW_INSTALL_URL" in install_sh

    def test_official_channel_defaults_latest(self, install_sh):
        assert "OPENCLAW_CHANNEL" in install_sh
        assert "latest" in install_sh

    def test_official_host_whitelist(self, install_sh):
        assert "openclaw.ai" in install_sh


# ── 回滚机制 (AGENT-001 §6.2) ───────────────────────────────────

class TestRollback:
    def test_rollback_function(self, install_sh):
        assert "rollback()" in install_sh

    def test_register_rollback(self, install_sh):
        assert "register_rollback" in install_sh


# ── 服务注册 ─────────────────────────────────────────────────────

class TestServiceRegistration:
    def test_systemd_unit(self, install_sh):
        assert "systemd" in install_sh

    def test_launchd_plist(self, install_sh):
        assert "launchd" in install_sh or "LaunchAgents" in install_sh

    def test_service_name(self, install_sh):
        assert "opc200-agent" in install_sh

    def test_systemctl_enable(self, install_sh):
        assert "systemctl enable" in install_sh

    def test_launchctl_load(self, install_sh):
        assert "launchctl load" in install_sh


# ── uninstall.sh ─────────────────────────────────────────────────

class TestUninstall:
    def test_service_stop(self, uninstall_sh):
        assert "systemctl stop" in uninstall_sh

    def test_launchctl_unload(self, uninstall_sh):
        assert "launchctl unload" in uninstall_sh

    def test_keep_data_option(self, uninstall_sh):
        assert "--keep-data" in uninstall_sh

    def test_silent_mode(self, uninstall_sh):
        assert "--silent" in uninstall_sh

    def test_root_check(self, uninstall_sh):
        assert "EUID" in uninstall_sh

    def test_removes_service_file(self, uninstall_sh):
        assert "systemd" in uninstall_sh or "service" in uninstall_sh


# ── 包管理器检测 ─────────────────────────────────────────────────

class TestPackageManagerDetection:
    MANAGERS = ["brew", "apt", "yum"]

    @pytest.mark.parametrize("mgr", MANAGERS)
    def test_pkg_manager_detected(self, install_sh, mgr):
        assert mgr in install_sh

    def test_detect_function(self, install_sh):
        assert "detect_pkg_manager" in install_sh


# ── 与 AGENT-001 SPEC 一致性 ────────────────────────────────────

class TestSpecConsistency:
    def test_three_config_items(self, install_sh):
        lower = install_sh.lower()
        for item in ("platform_url", "customer_id", "api_key"):
            assert item in lower

    def test_health_endpoint(self, install_sh):
        assert "/health" in install_sh

    def test_default_port_8080(self, install_sh):
        assert "8080" in install_sh

    def test_os_detection(self, install_sh):
        assert "uname" in install_sh

    def test_arch_detection(self, install_sh):
        for arch in ("amd64", "arm64"):
            assert arch in install_sh
