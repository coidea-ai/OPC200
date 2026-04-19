#Requires -Version 5.1
<#
.SYNOPSIS
    Bootstrap: download Release bundle + SHA256SUMS, verify, unzip, run install.ps1.
.PARAMETER Version
    Semver without v, or "latest". Default: $env:OPC200_INSTALL_VERSION or latest.
.PARAMETER GitHubRepo
    owner/repo. Default: $env:OPC200_GITHUB_REPO (required if unset).
.PARAMETER DownloadOnly
    Only download and verify; do not run install.ps1.
#>
param(
    [string]$Version = "",
    [string]$GitHubRepo = "",
    [string]$ExtractParent = "",
    [switch]$DownloadOnly,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallPassthrough
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:E004 = 4

function Get-GitHubHeaders {
    $h = @{
        "User-Agent"       = "opc200-bootstrap"
        "Accept"           = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    if ($env:GITHUB_TOKEN) {
        $h["Authorization"] = "Bearer $($env:GITHUB_TOKEN)"
    }
    return $h
}

function Resolve-VersionAndUrls {
    param([string]$Ver, [string]$Repo)
    $base = "https://github.com/$Repo"
    $api = "https://api.github.com/repos/$Repo"
    if ($Ver -eq "latest" -or -not $Ver) {
        $rel = Invoke-RestMethod -Uri "$api/releases/latest" -Headers (Get-GitHubHeaders) -Method Get
        $tag = $rel.tag_name
        if ($tag -notmatch '^v') { throw "Unexpected tag_name: $tag" }
        $sem = $tag.Substring(1)
        $zipName = "opc200-agent-$sem.zip"
        $asset = $rel.assets | Where-Object { $_.name -eq $zipName } | Select-Object -First 1
        if (-not $asset) {
            throw "Release asset not found: $zipName (tag $tag)"
        }
        return @{
            SemVer        = $sem
            Tag           = $tag
            ZipUrl        = $asset.browser_download_url
            SumsUrl       = "$base/releases/download/$tag/SHA256SUMS"
            ZipName       = $zipName
        }
    }
    $tag = "v$Ver"
    $zipName = "opc200-agent-$Ver.zip"
    return @{
        SemVer  = $Ver
        Tag     = $tag
        ZipUrl  = "$base/releases/download/$tag/$zipName"
        SumsUrl = "$base/releases/download/$tag/SHA256SUMS"
        ZipName = $zipName
    }
}

function Test-Sha256Sum {
    param(
        [string]$SumsPath,
        [string]$ZipPath,
        [string]$ZipName
    )
    $text = Get-Content -LiteralPath $SumsPath -Raw
    $expected = $null
    foreach ($line in ($text -split "`r?`n")) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        if ($t -match '^([a-fA-F0-9]{64})\s+[*]?(.+)$') {
            $fn = $matches[2].Trim()
            if ($fn -eq $ZipName) {
                $expected = $matches[1].ToLowerInvariant()
                break
            }
        }
    }
    if (-not $expected) { throw "SHA256SUMS: no entry for $ZipName" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        throw "SHA256 mismatch for $ZipName (expected $expected, got $actual)"
    }
}

if (-not $Version) {
    $Version = $env:OPC200_INSTALL_VERSION
    if (-not $Version) { $Version = "latest" }
}
if (-not $GitHubRepo) {
    $GitHubRepo = $env:OPC200_GITHUB_REPO
}
if (-not $GitHubRepo) {
    throw "Set -GitHubRepo or OPC200_GITHUB_REPO (owner/repo)"
}
if ($GitHubRepo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    throw "Invalid GitHubRepo: $GitHubRepo"
}

$info = Resolve-VersionAndUrls -Ver $Version -Repo $GitHubRepo
$destRoot = if ($ExtractParent) {
    $ExtractParent
} else {
    Join-Path $HOME (Join-Path ".opc200" (Join-Path "agent-bundle" $info.SemVer))
}
$null = New-Item -ItemType Directory -Force -Path $destRoot
$sumsPath = Join-Path $destRoot "SHA256SUMS"
$zipPath = Join-Path $destRoot $info.ZipName

try {
    Invoke-WebRequest -Uri $info.SumsUrl -OutFile $sumsPath -UseBasicParsing
    Invoke-WebRequest -Uri $info.ZipUrl -OutFile $zipPath -UseBasicParsing
    Test-Sha256Sum -SumsPath $sumsPath -ZipPath $zipPath -ZipName $info.ZipName

    $agentDir = Join-Path $destRoot "agent"
    if (Test-Path -LiteralPath $agentDir) {
        Remove-Item -LiteralPath $agentDir -Recurse -Force
    }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $destRoot -Force

    $installPs1 = Join-Path $destRoot "agent\scripts\install.ps1"
    if (-not (Test-Path -LiteralPath $installPs1)) {
        throw "install.ps1 not found under extracted bundle (expected agent\scripts\install.ps1 under $destRoot)"
    }
    $repoRootResolved = (Resolve-Path -LiteralPath $destRoot).Path

    if ($DownloadOnly) {
        Write-Host "Download OK; RepoRoot=$repoRootResolved"
        exit 0
    }

    & $installPs1 -RepoRoot $repoRootResolved @InstallPassthrough
}
catch {
    Write-Error $_
    exit $script:E004
}
