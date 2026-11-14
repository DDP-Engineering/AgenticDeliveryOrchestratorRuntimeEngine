:: Copyright (c) 2026 DDP Engineering
:: This software is licensed under the PolyForm Noncommercial License 1.0.0.
:: Commercial use requires a separate commercial license.
:: See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
@echo off
setlocal
set "PYTHONPATH="
set "PYTHONHOME="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%~dp0python\python.exe" -I -B -m adore %*
exit /b %ERRORLEVEL%
