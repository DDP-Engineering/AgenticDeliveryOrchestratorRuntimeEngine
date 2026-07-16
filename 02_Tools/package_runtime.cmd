:: -----------------------------------------------------------------------------
:: Copyright (c) 2026 DDP Engineering
:: This software is licensed under the PolyForm Noncommercial License 1.0.0.
:: Commercial use requires a separate commercial license.
:: See the LICENSE.txt file for full license details.
:: SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
:: -----------------------------------------------------------------------------
:: @file    package_runtime.cmd
:: @brief   CMD wrapper for the ADORE runtime packaging script.
:: @details Delegates to package_runtime.ps1 so Windows users can invoke the
::          same packager from cmd.exe, scripts, or CI jobs.
:: @usage   02_Tools\package_runtime.cmd [-OutputDir 07_Delivery]
::              [-Format zip|directory] [-IncludeConfig] [-PackageName NAME]
:: @author  Eng. Dan Dumitru Pasare
:: @date    2026-07-06
:: @version 0.2.0
:: -----------------------------------------------------------------------------
@echo off
setlocal

:: Stage 1: locate the PowerShell implementation next to this wrapper.
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%package_runtime.ps1"

:: Stage 2: fail closed if the wrapper was copied without its implementation.
if not exist "%PS_SCRIPT%" (
    echo error: package_runtime.ps1 not found next to this wrapper
    exit /b 1
)

:: Stage 3: delegate all arguments to the PowerShell packager.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
exit /b %ERRORLEVEL%

:: END OF FILE
