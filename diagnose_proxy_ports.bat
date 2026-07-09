@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Testing common local proxy ports...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "foreach($p in 7890,10809,10808,2080,2081,8080){$ok=Test-NetConnection 127.0.0.1 -Port $p -InformationLevel Quiet; if($ok){Write-Host ('OPEN  127.0.0.1:'+$p) -ForegroundColor Green}else{Write-Host ('CLOSED 127.0.0.1:'+$p) -ForegroundColor DarkGray}}"
echo.
echo If a port is OPEN it is not always HTTP. PowerShell Invoke-RestMethod needs HTTP/HTTPS proxy, not pure SOCKS.
pause
