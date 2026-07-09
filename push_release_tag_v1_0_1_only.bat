@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo This only creates/pushes tag v1.0.1. Use it if main was already pushed but tag push failed.
echo It auto-retries common Git proxies.
echo.
set /p GH_OWNER=GitHub owner [mcodersir]: 
if "%GH_OWNER%"=="" set "GH_OWNER=mcodersir"
set /p GH_REPO=GitHub repo [DicodeConfigChecker]: 
if "%GH_REPO%"=="" set "GH_REPO=DicodeConfigChecker"
set /p GIT_PROXY=Git proxy for push [optional/auto]: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push_release_tag_only.ps1" -Owner "%GH_OWNER%" -RepoName "%GH_REPO%" -Tag "v1.0.1" -GitProxy "%GIT_PROXY%"
pause
