# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
# @file    install-windows.ps1
# @brief   Deploy ADOR on Windows 11 (design doc 12/12a).
# @details Fail-fast, idempotent, re-runnable; Windows PowerShell 5.1
#          compatible. Steps: check host prerequisites, sync the Python
#          environment (uv), validate config.toml, verify the executor/base image
#          exists for the configured runtime, and optionally register a Task
#          Scheduler job - either the long-running poll loop at logon (-Mode
#          loop, the default) or a repeating single pass (-Mode once
#          -IntervalMinutes N). Secrets are never echoed and never appear in
#          argv; ADOR reads .env from its working directory (design 12b).
# @usage   .\deploy\install-windows.ps1 [-Mode loop|once] [-IntervalMinutes 10]
#              [-Runtime "docker"] [-ImageTag "ador-executor-base:0.2.0"]
#              [-SkipImageCheck] [-AllowOpenEgress] [-NoTask] [-Uninstall]
#          With Docker Engine in WSL2: -Runtime "wsl -d Ubuntu-24.04 -- docker"
# @author  Eng. Dan Dumitru Pasare
# @date    2026-07-04
# @version 0.3.0
# -----------------------------------------------------------------------------
[CmdletBinding()]
param(
    [ValidateSet("loop", "once")]
    [string]$Mode = "loop",
    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 10,
    [string]$Runtime = "docker",
    [string]$ImageTag = "ador-executor-base:0.2.0",
    [switch]$SkipImageCheck,
    [switch]$AllowOpenEgress,
    [switch]$NoTask,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# CONSTANTS
$TaskName    = "ADOR Orchestrator"
$SoftwareDir = Split-Path -Parent $PSScriptRoot
$AdorExe     = Join-Path $SoftwareDir ".venv\Scripts\ador.exe"

# LOCAL HELPERS
function Fail([string]$Message) {
    Write-Host "error: $Message" -ForegroundColor Red
    exit 1
}
function Note([string]$Message) {
    Write-Host "==> $Message"
}
function Need-Command([string]$Name, [string]$Hint) {
    if ($null -eq (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "'$Name' not found. $Hint"
    }
}

# UNINSTALL
if ($Uninstall) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Note "removed scheduled task '$TaskName' (worktrees, containers, and .ador state are kept)"
    } else {
        Note "no scheduled task '$TaskName'; nothing to do"
    }
    exit 0
}

# INSTALL - 1. host prerequisites (fail closed with a hint, never auto-install)
Note "checking host prerequisites"
Need-Command uv  "Install: winget install astral-sh.uv"
Need-Command git "Install: winget install Git.Git"
$glab = Get-Command glab -ErrorAction SilentlyContinue
$gh   = Get-Command gh   -ErrorAction SilentlyContinue
if ($null -eq $glab -and $null -eq $gh) {
    Fail "neither 'glab' nor 'gh' found; ADOR drives the platform through one of them (setup doc section 3)"
}

# 2. Python environment (locked, reproducible)
Note "syncing the Python environment (uv sync --frozen)"
Push-Location $SoftwareDir
try {
    uv sync --frozen
    if ($LASTEXITCODE -ne 0) { Fail "uv sync failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}
if (-not (Test-Path $AdorExe)) { Fail ".venv\Scripts\ador.exe missing after uv sync" }

# 3. configuration (catch problems here where the operator is watching)
if (-not (Test-Path (Join-Path $SoftwareDir "config.toml"))) {
    Fail "config.toml not found; copy config.example.toml and adjust it first"
}
Note "validating config.toml"
Push-Location $SoftwareDir
try {
    & $AdorExe -c config.toml config validate
    if ($LASTEXITCODE -ne 0) { Fail "config validation failed" }
    $ConfigData = (& $AdorExe -c config.toml config show | Out-String | ConvertFrom-Json)
} finally {
    Pop-Location
}
$EgressMode = [string]$ConfigData.container.egress.mode
$ProxyImage = [string]$ConfigData.container.egress.proxy_image
if (-not $NoTask -and $EgressMode -eq "open" -and -not $AllowOpenEgress) {
    Fail "refusing unattended Task Scheduler install with [container.egress] mode='open'; set allowlist-proxy/none or pass -AllowOpenEgress for a supervised pilot"
}
if (-not (Test-Path (Join-Path $SoftwareDir ".env"))) {
    Note "note: no .env file (fine when glab/gh host auth covers everything;"
    Note "      see .env.example for the canonical secret list)"
}

# 4. executor image (verify only - building through a wrapped runtime needs
#    WSL path translation, so the build command lives in docker/README.md)
if (-not $SkipImageCheck) {
    $runtimeArgv = $Runtime -split "\s+"
    $runtimeExe = $runtimeArgv[0]
    Need-Command $runtimeExe "Configure [container] runtime, or re-run with -SkipImageCheck"
    $inspectArgs = @()
    if ($runtimeArgv.Count -gt 1) { $inspectArgs += $runtimeArgv[1..($runtimeArgv.Count - 1)] }
    $inspectArgs += @("image", "inspect", $ImageTag)
    & $runtimeExe @inspectArgs *> $null
    if ($LASTEXITCODE -ne 0) {
        Note "executor image '$ImageTag' not found via runtime '$Runtime'."
        Note "Build it first (exact commands, incl. the WSL2 variant, in docker\README.md), e.g.:"
        Note "    cd $SoftwareDir\docker; docker build --build-arg USER_UID=`$(id -u) -f Dockerfile.executor-base -t ador-executor-base:0.2.0 ."
        Note "For Cockpit-GCP also build: docker build -f Dockerfile.executor-cockpit-gcp -t ador-executor-cockpit-gcp:latest ."
        Fail "executor image missing"
    }
    Note "executor image $ImageTag present"
} else {
    Note "skipping executor image check (-SkipImageCheck)"
}

if ($EgressMode -eq "allowlist-proxy") {
    $runtimeArgv = $Runtime -split "\s+"
    $runtimeExe = $runtimeArgv[0]
    Need-Command $runtimeExe "Configure [container] runtime before using allowlist-proxy"
    $inspectArgs = @()
    if ($runtimeArgv.Count -gt 1) { $inspectArgs += $runtimeArgv[1..($runtimeArgv.Count - 1)] }
    $inspectArgs += @("image", "inspect", $ProxyImage)
    & $runtimeExe @inspectArgs *> $null
    if ($LASTEXITCODE -ne 0) {
        Note "egress proxy image '$ProxyImage' not found via runtime '$Runtime'."
        Note "Build it first with:"
        Note "    cd $SoftwareDir\docker; docker build -f Dockerfile.egress-proxy -t $ProxyImage ."
        Note "For WSL2 Docker, run inside the distro with the /mnt/... path to this docker directory."
        Fail "egress proxy image missing"
    }
    Note "egress proxy image $ProxyImage present"
}

# 5. Task Scheduler job (optional; the design's Windows service mode, 12a)
if ($NoTask) {
    Note "prepared (no task registered). Run the poller manually with:"
    Note "    cd $SoftwareDir; .\.venv\Scripts\ador.exe run --loop"
    exit 0
}

Note "registering scheduled task '$TaskName' (mode: $Mode)"
if ($Mode -eq "loop") {
    # Long-running poller: start at logon, no execution time limit; the
    # instance lock (.ador\ador.lock) prevents accidental double pollers.
    $action  = New-ScheduledTaskAction -Execute $AdorExe `
        -Argument "-c config.toml run --loop" -WorkingDirectory $SoftwareDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
} else {
    # Repeating single pass: one poll every N minutes, first run one minute
    # from now; each pass exits, so a wedged pass cannot block the schedule.
    $action  = New-ScheduledTaskAction -Execute $AdorExe `
        -Argument "-c config.toml run --once" -WorkingDirectory $SoftwareDir
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
}
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Note "replaced existing task"
}
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings `
    -Description "ADOR - Agentic Delivery Orchestrator (design 12a)" | Out-Null

Note "task registered. Start it now with:  Start-ScheduledTask -TaskName '$TaskName'"
Note "inspect runs in Task Scheduler or with:  Get-ScheduledTaskInfo -TaskName '$TaskName'"

# END OF FILE
