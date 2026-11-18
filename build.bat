@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build.ps1" %*
set "CODE=%ERRORLEVEL%"

echo.
if not "%CODE%"=="0" echo Build failed with exit code %CODE%.
echo Press any key to close this window.
pause >nul

exit /b %CODE%
