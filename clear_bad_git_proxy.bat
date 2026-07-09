@echo off
chcp 65001 >nul
echo Removing global Git proxy settings if they exist...
git config --global --unset http.proxy 2>nul
git config --global --unset https.proxy 2>nul
git config --global --unset-all http.proxy 2>nul
git config --global --unset-all https.proxy 2>nul
echo Done. This only clears Git global proxy config, not your Windows/VPN settings.
pause
