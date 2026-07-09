@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Use this only if release\DicodeConfigChecker-v1.0.1-windows.exe already exists.
echo Enter your local HTTP proxy. Examples:
echo   http://127.0.0.1:7890
echo   http://127.0.0.1:10809
echo.
set /p DICODE_PROXY=Proxy URL: 
if "%DICODE_PROXY%"=="" (
  echo Proxy is empty.
  pause
  exit /b 1
)
set HTTP_PROXY=%DICODE_PROXY%
set HTTPS_PROXY=%DICODE_PROXY%
set ALL_PROXY=%DICODE_PROXY%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_to_github.ps1" -Tag "v1.0.1" -PreviousTag "v1.0.0" -Proxy "%DICODE_PROXY%" -SkipBuild
pause
