@echo off
chcp 65001 >nul
echo === DNS check ===
nslookup github.com

echo.
echo === Common local proxy ports ===
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports=10809,10808,7890,7891,2080,1080; foreach($p in $ports){$ok=Test-NetConnection 127.0.0.1 -Port $p -InformationLevel Quiet; if($ok){Write-Host ('OPEN  127.0.0.1:'+$p) -ForegroundColor Green}else{Write-Host ('closed 127.0.0.1:'+$p) -ForegroundColor DarkGray}}"

echo.
echo === Git direct test ===
git ls-remote https://github.com/github/docs.git HEAD

echo.
echo If direct test failed with DNS, run deploy_via_github_actions_v1_0_1.bat and enter one open proxy port:
echo   http://127.0.0.1:10809
echo   socks5h://127.0.0.1:10808
echo   http://127.0.0.1:7890
echo   socks5h://127.0.0.1:7891
pause
