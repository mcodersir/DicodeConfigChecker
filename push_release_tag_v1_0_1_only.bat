@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Push only tag v1.0.1. No proxy is used unless you explicitly enter one.
echo.
set /p GH_OWNER=GitHub owner [mcodersir]: 
if "%GH_OWNER%"=="" set "GH_OWNER=mcodersir"
set /p GH_REPO=GitHub repo [DicodeConfigChecker]: 
if "%GH_REPO%"=="" set "GH_REPO=DicodeConfigChecker"
set /p GIT_PROXY=Git proxy for tag push [empty = no proxy]: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push_release_tag_only.ps1" -Owner "%GH_OWNER%" -RepoName "%GH_REPO%" -Tag "v1.0.1" -GitProxy "%GIT_PROXY%"
pause
