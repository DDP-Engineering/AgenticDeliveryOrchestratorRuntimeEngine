@echo off
setlocal
"%~dp0python\python.exe" -I -B "%~dp0launch.py" %*
set "ADORE_RESULT=%ERRORLEVEL%"
if not "%ADORE_RESULT%"=="0" (
    echo ADORE could not start. See the error above and the displayed log location.
    if "%~1"=="" pause
)
exit /b %ADORE_RESULT%
