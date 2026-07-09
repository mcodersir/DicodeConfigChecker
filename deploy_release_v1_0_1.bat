@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_to_github.ps1" -Tag "v1.0.1" -PreviousTag "v1.0.0"
pause
