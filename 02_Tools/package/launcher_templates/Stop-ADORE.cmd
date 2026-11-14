:: Copyright (c) 2026 DDP Engineering
:: This software is licensed under the PolyForm Noncommercial License 1.0.0.
:: Commercial use requires a separate commercial license.
:: See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
@echo off
setlocal
"%~dp0python\python.exe" -I -B "%~dp0launch.py" --stop %*
exit /b %ERRORLEVEL%
