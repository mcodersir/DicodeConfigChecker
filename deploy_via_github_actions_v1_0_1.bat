@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo This deploy method does NOT call api.github.com from your PC.
echo It only pushes source and tag. GitHub Actions builds the EXE and creates the release on GitHub servers.
echo.
echo Proxy behavior changed:
echo   - Leave empty = NO proxy, direct Git only.
echo   - The script will NOT auto-try proxy ports.
echo   - Enter a proxy only if you explicitly want Git to use one.
echo.
echo Optional proxy examples:
echo   http://127.0.0.1:10809
echo   http://127.0.0.1:7890
echo   socks5h://127.0.0.1:10808
echo.
set /p GH_OWNER=GitHub owner [mcodersir]: 
if "%GH_OWNER%"=="" set "GH_OWNER=mcodersir"
set /p GH_REPO=GitHub repo [DicodeConfigChecker]: 
if "%GH_REPO%"=="" set "GH_REPO=DicodeConfigChecker"
set /p GIT_PROXY=Git proxy for push [empty = no proxy]: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_via_github_actions.ps1" -Owner "%GH_OWNER%" -RepoName "%GH_REPO%" -Tag "v1.0.1" -GitProxy "%GIT_PROXY%"
pause
