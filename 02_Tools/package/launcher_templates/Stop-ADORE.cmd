@echo off
setlocal
"%~dp0python\python.exe" -I -B "%~dp0launch.py" --stop %*
exit /b %ERRORLEVEL%
