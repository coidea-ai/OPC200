from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "agent" / "scripts"


def _ps1() -> str:
    return (SCRIPTS_DIR / "openclaw-installer.ps1").read_text(encoding="utf-8")


def _sh() -> str:
    return (SCRIPTS_DIR / "openclaw-installer.sh").read_text(encoding="utf-8")


def _build_ps1() -> str:
    return (SCRIPTS_DIR / "build-openclaw-installer-exe.ps1").read_text(encoding="utf-8")


def _uninstall_ps1() -> str:
    return (SCRIPTS_DIR / "openclaw-uninstaller.ps1").read_text(encoding="utf-8")


def _build_uninstall_ps1() -> str:
    return (SCRIPTS_DIR / "build-openclaw-uninstaller-exe.ps1").read_text(encoding="utf-8")


def _pack_ps1() -> str:
    return (SCRIPTS_DIR / "pack-openclaw-installer-release.ps1").read_text(encoding="utf-8")


def test_openclaw_installer_ps1_has_expected_steps():
    s = _ps1()
    assert "Run-HardChecks" in s
    assert "Get-NodeMajorVersion" in s
    assert "Install-NodeFromOfflineBundle" in s
    assert "node-v22.22.2" in s
    assert "node-v22.22.2-win-x64.zip" in s
    assert "node-v22.22.2-win-x86.zip" in s
    assert "openclaw.ai" in s
    assert "Get-NetTCPConnection" in s
    assert "Create-DesktopShortcuts" in s
    assert "Show-InstallSuccessDialog" in s
    assert "System.Windows.Forms.MessageBox" in s
    assert "Start-Process $url" in s
    assert "Get-DashboardUrlFromCli" in s
    assert "Dashboard URL:" in s
    assert "openclaw dashboard" in s or 'ArgumentList @("dashboard")' in s
    assert "openclaw-gateway-start.ps1" in s
    assert "openclaw-gateway-stop.ps1" in s
    assert "Invoke-WebRequest -Uri" in s
    assert "& openclaw gateway start" in s
    assert 'New-DesktopShortcut -Name "OpenClaw Start"' in s
    assert 'New-DesktopShortcut -Name "OpenClaw Stop"' in s
    assert "Install-OpenClawFromBundledZip" in s
    assert "Run-Onboard" in s
    assert "Write-TemplatesAndSkills" in s
    assert "Configure-Gateway" in s
    assert "onboard --non-interactive --accept-risk" in s
    assert 'Join-Path $script:ReleaseDir ("OpenClaw-" + $script:ReleaseVersion + ".zip")' in s


def test_openclaw_installer_sh_has_expected_steps():
    s = _sh()
    assert "install_openclaw_macos" in s
    assert "run_onboard" in s
    assert "preinstall_assets" in s
    assert "configure_gateway" in s
    assert "openclaw onboard --non-interactive --accept-risk" in s
    assert 'DMG_PATH="${RELEASE_DIR}/OpenClaw-2026.4.15.dmg"' in s


def test_openclaw_installer_exe_build_script_present():
    s = _build_ps1()
    assert "Invoke-ps2exe" in s
    assert "OpenClawInstaller.exe" in s
    assert "Install-Module -Name ps2exe" in s


def test_openclaw_uninstaller_scripts_present():
    s = _uninstall_ps1()
    assert "uninstall --all --yes --non-interactive" in s
    assert "gateway stop" in s
    b = _build_uninstall_ps1()
    assert "Invoke-ps2exe" in b
    assert "OpenClawUninstaller.exe" in b


def test_openclaw_release_pack_script_present():
    s = _pack_ps1()
    assert "OpenClawInstaller.zip" in s
    assert "OpenClawInstaller.exe" in s
    assert "OpenClawUninstaller.exe" in s
    assert "openclaw-releases" in s
    assert "openclaw-templates" in s
    assert "node-v22.22.2" in s
    assert "node-v22.22.2-win-x64.zip" in s
    assert "node-v22.22.2-win-x86.zip" in s
