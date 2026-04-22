from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "agent" / "scripts"


def _ps1() -> str:
    return (SCRIPTS_DIR / "openclaw-installer.ps1").read_text(encoding="utf-8-sig")


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
    assert 'Write-Step "1/6 环境检测（硬检测）"' in s
    assert 'Write-Step "6/6 创建桌面快捷方式"' in s
    assert "Test-IsAdministrator" in s
    assert "当前以管理员身份运行" in s
    assert "WindowsBuiltInRole]::Administrator" in s
    assert "Get-NodeVersionLine" in s
    assert "Test-NodeMatchesPinned" in s
    assert "Install-NodeFromOfflineBundle" in s
    assert "node-v22.22.2" in s
    assert "node-v22.22.2-win-x64.zip" in s
    assert "node-v22.22.2-win-x86.zip" in s
    assert "openclaw.ai" in s
    assert "Get-NetTCPConnection" in s
    assert "Try-ReleaseLocalPort" in s
    assert "Test-NoListenerOnGatewayPort" in s
    assert "-State Listen" in s
    assert "Get-LocalPortConnSummary" in s
    assert "gateway stop" in s
    assert "OpenClaw Gateway" in s
    assert "Create-DesktopShortcuts" in s
    assert "Show-InstallSuccessDialog" in s
    assert "Open-DashboardUrlInBrowser" in s
    assert "UseShellExecute" in s
    assert "System.Windows.Forms.MessageBox" in s
    assert "[System.Text.UTF8Encoding]::new($true)" in s
    assert "Get-DashboardUrlFromCli" in s
    assert "Start-Job" in s
    assert "Wait-Job" in s
    assert "Read-DashboardUrlFromCliOutput" in s
    assert "access_token" in s
    assert "FromBase64String" in s
    assert r"Dashboard\s+URL" in s
    assert "openclaw dashboard" in s or 'ArgumentList @("dashboard")' in s
    assert "openclaw-gateway-start.ps1" in s
    assert "for (`$ti = 1; `$ti -le 2" in s
    assert "openclaw-gateway-stop.ps1" in s
    assert "Invoke-WebRequest -Uri" in s
    assert "& openclaw gateway start" in s
    assert 'New-DesktopShortcut -Name "OpenClaw Start"' in s
    assert 'New-DesktopShortcut -Name "OpenClaw Stop"' in s
    assert "Install-OpenClawFromOfflineNpm" in s
    assert "SkipInstallOpenClawFromNpm" in s
    assert "OpenClaw 版本:" in s
    assert "openclaw-npm-cache" in s
    assert "npm_config_cache" in s
    assert 'OpenClawNpmVersion = "2026.4.15"' in s
    assert "Run-Onboard" in s
    assert "请选择需要配置的模型" in s
    assert "选择 [ABCD 其中一个]" in s
    assert "OpenClaw 自定义模型的 Base Url" in s
    assert "Invoke-OpenClawLongRunning" in s
    assert "Format-CmdExeMetacharToken" in s
    assert '@("/d", "/s", "/c"' in s
    assert "Write-TemplatesAndSkills" in s
    assert "Configure-Gateway" in s
    assert "Wait-GatewayRpcReady" in s
    assert "gateway install --force --port" in s
    assert '"onboard", "--non-interactive", "--accept-risk", "--mode", "local",' in s
    assert "--skip-health" in s
    assert "gateway install" in s


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
    assert "npm uninstall -g openclaw" in s
    assert "Uninstall-OpenClawNpmGlobal" in s
    assert "Remove-OpenClawStateDirectories" in s
    assert "Remove-ReleaseBundleArtifacts" in s
    assert "OpenClawInstaller.zip" in s
    assert "rd /s /q" in s
    assert "LOCALAPPDATA" in s and "OpenClaw" in s
    assert "Remove-InstallerDesktopArtifacts" in s
    assert "OpenClaw Start" in s
    assert "OpenClawInstaller" in s
    b = _build_uninstall_ps1()
    assert "Invoke-ps2exe" in b
    assert "OpenClawUninstaller.exe" in b


def test_openclaw_release_pack_script_present():
    s = _pack_ps1()
    assert "OpenClawInstaller.zip" in s
    assert "OpenClawInstaller.exe" in s
    assert "OpenClawUninstaller.exe" in s
    assert "openclaw-npm-cache" in s
    assert "openclaw-templates" in s
    assert "node-v22.22.2" in s
    assert "node-v22.22.2-win-x64.zip" in s
    assert "node-v22.22.2-win-x86.zip" in s
