# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
# @file    package_runtime.ps1
# @brief   Build a trimmed ADOR runtime bundle on Windows.
# @details Creates a deployable bundle from 04_Software without development
#          state, tests, worktrees, caches, or virtual environments. The bundle
#          includes the existing deploy scripts for Windows Task Scheduler and
#          Ubuntu systemd setup.
# @usage   .\02_Tools\package_runtime.ps1 [-OutputDir 07_Delivery]
#              [-Format zip|directory] [-IncludeConfig] [-PackageName NAME]
# @author  Eng. Dan Dumitru Pasare
# @date    2026-07-06
# @version 0.1.0
# -----------------------------------------------------------------------------
[CmdletBinding()]
param(
    [string]$OutputDir,
    [ValidateSet("zip", "directory")]
    [string]$Format = "zip",
    [switch]$IncludeConfig,
    [string]$PackageName
)

$ErrorActionPreference = "Stop"

# CONSTANTS
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$SoftwareDir = Join-Path $RepoRoot "04_Software"
if (-not $OutputDir) {
    $OutputDir = Join-Path $RepoRoot "07_Delivery"
}

# LOCAL HELPERS
function Fail([string]$Message) {
    Write-Host "error: $Message" -ForegroundColor Red
    exit 1
}

function Note([string]$Message) {
    Write-Host "==> $Message"
}

function Remove-TreeInside([string]$Target, [string]$AllowedRoot) {
    $rootFull = (Resolve-Path -LiteralPath $AllowedRoot).Path
    $targetParent = Split-Path -Parent $Target
    if ($targetParent -and (Test-Path -LiteralPath $targetParent)) {
        $parentFull = (Resolve-Path -LiteralPath $targetParent).Path
        if ($parentFull -ne $rootFull) {
            Fail "refusing to remove path outside output directory: $Target"
        }
    } else {
        Fail "refusing to remove path with missing parent: $Target"
    }
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
}

function Copy-Required([string]$RelativePath, [string]$DestinationRoot) {
    $source = Join-Path $SoftwareDir $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        Fail "required runtime path missing: 04_Software\$RelativePath"
    }
    $destination = Join-Path $DestinationRoot $RelativePath
    $destinationParent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

function Read-PackageVersion {
    $pyproject = Join-Path $SoftwareDir "pyproject.toml"
    $match = Select-String -LiteralPath $pyproject -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $match) {
        Fail "could not read project version from 04_Software\pyproject.toml"
    }
    return $match.Matches[0].Groups[1].Value
}

function Write-BundleReadme([string]$DestinationRoot, [string]$Version) {
    $readme = @'
# ADOR Runtime Bundle

Version: __VERSION__

This bundle contains only the files needed to run ADOR as a Python package.
It intentionally excludes tests, worktrees, .ador state, caches, and .venv.

Prepare:

```powershell
uv sync --frozen
copy config.example.toml config.toml
notepad config.toml
```

Windows service-style setup:

```powershell
.\deploy\install-windows.ps1 -NoTask
.\deploy\install-windows.ps1
```

Ubuntu service-style setup:

```bash
bash deploy/install-ubuntu.sh
bash deploy/install-ubuntu.sh --service
```

Secrets belong in `.env` beside this file or in host CLI authentication.
The package never includes `.env`.
'@
    $readme = $readme -replace "__VERSION__", $Version
    $readme | Set-Content -LiteralPath (Join-Path $DestinationRoot "README_PACKAGED.md") -Encoding UTF8
}

# PUBLIC SCRIPT FLOW

# Stage 1: verify the expected repository layout exists.
if (-not (Test-Path -LiteralPath $SoftwareDir)) {
    Fail "04_Software not found next to 02_Tools"
}

# Stage 2: read the project release version and derive a safe package name.
$version = Read-PackageVersion
if (-not $PackageName) {
    $PackageName = "ador-runtime-$version"
}
if ($PackageName -match '[\\/]' -or $PackageName -match '^\.+$') {
    Fail "package name must be a single directory name, not a path: $PackageName"
}

# Stage 3: prepare the output and temporary staging directories.
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputFull = (Resolve-Path -LiteralPath $OutputDir).Path
$stageRoot = Join-Path $outputFull ".packaging_tmp"
$bundleDir = Join-Path $stageRoot $PackageName

Note "staging ADOR runtime bundle $PackageName"
Remove-TreeInside $stageRoot $outputFull
New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null

# Stage 4: copy only the runtime files needed by the deployment host.
$runtimePaths = @(
    "ador",
    "deploy",
    "docker",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "config.example.toml",
    ".env.example"
)
foreach ($path in $runtimePaths) {
    Copy-Required $path $bundleDir
}

# Stage 5: remove generated Python caches from copied runtime directories.
Get-ChildItem -LiteralPath $bundleDir -Directory -Recurse -Filter "__pycache__" |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $bundleDir -File -Recurse |
    Where-Object { $_.Extension -eq ".pyc" -or $_.Extension -eq ".pyo" } |
    Remove-Item -Force

# Stage 6: include root release notes when present.
$rootChangelog = Join-Path $RepoRoot "CHANGELOG.md"
if (Test-Path -LiteralPath $rootChangelog) {
    Copy-Item -LiteralPath $rootChangelog -Destination (Join-Path $bundleDir "CHANGELOG.md") -Force
}

# Stage 7: optionally include the target config, but never include secrets.
if ($IncludeConfig) {
    Copy-Required "config.toml" $bundleDir
    Note "included config.toml by explicit request; .env is still excluded"
}

# Stage 8: write short unpack-and-deploy instructions into the bundle.
Write-BundleReadme $bundleDir $version

# Stage 9: either keep the staged directory as the artifact or create a zip.
if ($Format -eq "directory") {
    $finalDir = Join-Path $outputFull $PackageName
    Remove-TreeInside $finalDir $outputFull
    Move-Item -LiteralPath $bundleDir -Destination $finalDir
    Remove-TreeInside $stageRoot $outputFull
    Note "wrote $finalDir"
    exit 0
}

# Stage 10: create the zip artifact and clean temporary staging files.
$archive = Join-Path $outputFull "$PackageName.zip"
if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive -Force
}
Compress-Archive -LiteralPath $bundleDir -DestinationPath $archive -Force
Remove-TreeInside $stageRoot $outputFull
Note "wrote $archive"

# END OF FILE
