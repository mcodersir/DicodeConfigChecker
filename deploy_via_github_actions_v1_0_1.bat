@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo This deploy method does NOT call api.github.com from your PC.
echo It only pushes source and tag. GitHub Actions builds the EXE and creates the release on GitHub servers.
echo.
echo If your Git says: Could not resolve host: github.com
echo enter your local proxy below if you know it. Leave empty to auto-try common proxies.
echo Examples:
echo   http://127.0.0.1:10809     ^(v2rayN HTTP / mixed, common^)
echo   http://127.0.0.1:7890      ^(Clash mixed, common^)
echo   socks5h://127.0.0.1:10808 ^(v2rayN SOCKS; DNS through proxy^)
echo   socks5h://127.0.0.1:7891  ^(Clash SOCKS; DNS through proxy^)
echo.
set /p GH_OWNER=GitHub owner [mcodersir]: 
if "%GH_OWNER%"=="" set "GH_OWNER=mcodersir"
set /p GH_REPO=GitHub repo [DicodeConfigChecker]: 
if "%GH_REPO%"=="" set "GH_REPO=DicodeConfigChecker"
set /p GIT_PROXY=Git proxy for push [optional/auto]: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_via_github_actions.ps1" -Owner "%GH_OWNER%" -RepoName "%GH_REPO%" -Tag "v1.0.1" -GitProxy "%GIT_PROXY%"
pause
