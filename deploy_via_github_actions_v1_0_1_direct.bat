@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Direct deploy without Git proxy.
set /p GH_OWNER=GitHub owner [mcodersir]: 
if "%GH_OWNER%"=="" set "GH_OWNER=mcodersir"
set /p GH_REPO=GitHub repo [DicodeConfigChecker]: 
if "%GH_REPO%"=="" set "GH_REPO=DicodeConfigChecker"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_via_github_actions.ps1" -Owner "%GH_OWNER%" -RepoName "%GH_REPO%" -Tag "v1.0.1"
pause
