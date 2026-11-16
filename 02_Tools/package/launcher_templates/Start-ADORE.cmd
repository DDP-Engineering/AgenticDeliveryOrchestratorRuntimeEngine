:: Copyright (c) 2026 DDP Engineering
:: This software is licensed under the PolyForm Noncommercial License 1.0.0.
:: Commercial use requires a separate commercial license.
:: See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
@echo off
setlocal
"%~dp0python\python.exe" -I -B "%~dp0launch.py" %*
set "ADORE_RESULT=%ERRORLEVEL%"
if not "%ADORE_RESULT%"=="0" (
    echo ADORE could not start. See the error above and the displayed log location.
    if "%~1"=="" pause
)
exit /b %ADORE_RESULT%
