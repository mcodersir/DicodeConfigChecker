@echo off
chcp 65001 >nul
echo == DNS test for api.github.com ==
nslookup api.github.com
echo.
echo == HTTPS test for GitHub API ==
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 https://api.github.com; Write-Host ('OK Status: ' + $r.StatusCode) -ForegroundColor Green } catch { Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }"
pause
