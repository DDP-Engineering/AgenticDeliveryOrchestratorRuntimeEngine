@echo off
setlocal
set "PYTHONPATH="
set "PYTHONHOME="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%~dp0python\python.exe" -I -B -m adore %*
exit /b %ERRORLEVEL%
