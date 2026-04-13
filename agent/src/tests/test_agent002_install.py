"""AGENT-002 单元测试: Windows 安装/卸载脚本与 AGENT-001 规范一致性检查"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "agent" / "scripts"
SPEC_PATH = REPO_ROOT / "docs" / "INSTALL_SCRIPT_SPEC.md"


@pytest.fixture(scope="module")
def install_ps1():
    return (SCRIPTS_DIR / "install.ps1").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def uninstall_ps1():
    return (SCRIPTS_DIR / "uninstall.ps1").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec_md():
    return SPEC_PATH.read_text(encoding="utf-8")


# ── 文件存在性 ────────────────────────────────────────────────────

class TestFilesExist:
    def test_install_script_exists(self):
        assert (SCRIPTS_DIR / "install.ps1").is_file()

    def test_uninstall_script_exists(self):
        assert (SCRIPTS_DIR / "uninstall.ps1").is_file()

    def test_spec_exists(self):
        assert SPEC_PATH.is_file()


# ── install.ps1 参数声明 ─────────────────────────────────────────

class TestInstallParams:
    REQUIRED_PARAMS = ["PlatformUrl", "CustomerId", "ApiKey", "InstallDir", "Port", "Silent"]

    @pytest.mark.parametrize("param", REQUIRED_PARAMS)
    def test_param_declared(self, install_ps1, param):
        assert param in install_ps1

    def test_requires_ps51(self, install_ps1):
        assert "#Requires -Version 5.1" in install_ps1


# ── 7 步流程函数 ─────────────────────────────────────────────────

class TestInstallSteps:
    STEP_FUNCTIONS = [
        "Test-Environment",
        "Get-InstallConfig",
        "Get-AgentBinary",
        "Install-Agent",
        "Register-Service",
        "Start-AndVerify",
        "Show-Summary",
    ]

    @pytest.mark.parametrize("func", STEP_FUNCTIONS)
    def test_step_function_defined(self, install_ps1, func):
        assert f"function {func}" in install_ps1


# ── 错误码 (AGENT-001 §6.1) ─────────────────────────────────────

class TestErrorCodes:
    CODES = {
        "E001": "权限不足",
        "E002": "网络连接失败",
        "E003": "端口占用",
        "E004": "校验失败",
        "E005": "服务注册失败",
    }

    @pytest.mark.parametrize("code", CODES.keys())
    def test_error_code_present(self, install_ps1, code):
        assert code in install_ps1


# ── 目录结构 (AGENT-001 §3.1) ───────────────────────────────────

class TestDirectoryStructure:
    SPEC_DIRS = ["bin", "config", "data", "journal", "exporter", "logs"]

    @pytest.mark.parametrize("d", SPEC_DIRS)
    def test_dir_in_script(self, install_ps1, d):
        assert d in install_ps1

    def test_default_install_dir(self, install_ps1):
        assert ".opc200" in install_ps1


# ── config.yml 模板 ──────────────────────────────────────────────

class TestConfigTemplate:
    def _extract_yaml_block(self, ps1_text: str) -> str:
        match = re.search(
            r'\$configYml\s*=\s*@"(.*?)"@',
            ps1_text,
            re.DOTALL,
        )
        assert match, "未找到 config.yml 模板"
        return match.group(1).strip()

    def test_yaml_parseable(self, install_ps1):
        raw = self._extract_yaml_block(install_ps1)
        raw = re.sub(r'\$\([^)]+\)', 'placeholder', raw)
        cfg = yaml.safe_load(raw)
        assert cfg is not None

    def test_contains_required_sections(self, install_ps1):
        raw = self._extract_yaml_block(install_ps1)
        for section in ("platform:", "customer:", "agent:", "gateway:", "journal:", "logging:"):
            assert section in raw


# ── .env 与安全 ──────────────────────────────────────────────────

class TestSecurity:
    def test_env_file_written(self, install_ps1):
        assert ".env" in install_ps1

    def test_acl_set(self, install_ps1):
        assert "Set-Acl" in install_ps1

    def test_api_key_secure_input(self, install_ps1):
        assert "AsSecureString" in install_ps1


# ── SHA256 校验 ──────────────────────────────────────────────────

class TestChecksum:
    def test_sha256_check(self, install_ps1):
        assert "SHA256" in install_ps1

    def test_checksum_file_referenced(self, install_ps1):
        assert "SHA256SUMS" in install_ps1


# ── 回滚机制 (AGENT-001 §6.2) ───────────────────────────────────

class TestRollback:
    def test_rollback_function(self, install_ps1):
        assert "Invoke-Rollback" in install_ps1

    def test_register_rollback(self, install_ps1):
        assert "Register-Rollback" in install_ps1


# ── 服务注册 ─────────────────────────────────────────────────────

class TestServiceRegistration:
    def test_service_name(self, install_ps1):
        assert "OPC200-Agent" in install_ps1

    def test_sc_create(self, install_ps1):
        assert "sc.exe create" in install_ps1

    def test_auto_start(self, install_ps1):
        assert "start= auto" in install_ps1


# ── uninstall.ps1 ────────────────────────────────────────────────

class TestUninstall:
    def test_requires_ps51(self, uninstall_ps1):
        assert "#Requires -Version 5.1" in uninstall_ps1

    def test_service_removal(self, uninstall_ps1):
        assert "sc.exe delete" in uninstall_ps1

    def test_keep_data_option(self, uninstall_ps1):
        assert "KeepData" in uninstall_ps1

    def test_silent_mode(self, uninstall_ps1):
        assert "Silent" in uninstall_ps1

    def test_admin_check(self, uninstall_ps1):
        assert "Administrator" in uninstall_ps1


# ── 与 AGENT-001 SPEC 一致性 ────────────────────────────────────

class TestSpecConsistency:
    def test_three_config_items(self, install_ps1):
        for item in ("PLATFORM_URL", "CUSTOMER_ID", "API_KEY"):
            assert item.lower().replace("_", "") in install_ps1.lower().replace("_", "")

    def test_health_endpoint(self, install_ps1):
        assert "/health" in install_ps1

    def test_default_port_8080(self, install_ps1):
        assert "8080" in install_ps1
