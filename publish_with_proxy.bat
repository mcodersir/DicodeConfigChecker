@echo off
setlocal
cd /d "%~dp0"
echo.
echo Dicode Config Checker - GitHub Publisher with Proxy Support
echo.
echo Common local HTTP proxy ports:
echo   v2rayN: http://127.0.0.1:10809
echo   Clash : http://127.0.0.1:7890
echo.
set /p GITHUB_PROXY=Proxy URL or host:port, leave empty for auto: 
if not "%GITHUB_PROXY%"=="" set GITHUB_PROXY=%GITHUB_PROXY%
powershell -ExecutionPolicy Bypass -File "%~dp0publish_to_github.ps1"
pause
