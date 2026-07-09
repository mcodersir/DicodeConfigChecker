@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_VERSION=1.0.1"
set "PYTHON_CMD=python"

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  py -3 --version >nul 2>&1
  if errorlevel 1 (
    echo Python was not found. Install Python 3.10+ and try again.
    goto fail
  )
  set "PYTHON_CMD=py -3"
)

if not exist "core" mkdir "core"

echo [1/4] Installing build requirements...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 goto fail
%PYTHON_CMD% -m pip install -r requirements-build.txt
if errorlevel 1 goto fail

echo [2/4] Preparing Xray-core before building...
if exist "core\xray.exe" goto xray_ready

echo Trying current network / system proxy...
call :download_xray
if exist "core\xray.exe" goto xray_ready

for %%P in (http://127.0.0.1:10809 http://127.0.0.1:7890 http://127.0.0.1:2080 http://127.0.0.1:2081 http://127.0.0.1:8080 http://localhost:10809 http://localhost:7890) do (
  echo Trying download proxy: %%P
  set "HTTP_PROXY=%%P"
  set "HTTPS_PROXY=%%P"
  set "http_proxy=%%P"
  set "https_proxy=%%P"
  set "DOWNLOAD_PROXY=%%P"
  call :download_xray
  if exist "core\xray.exe" goto xray_ready
)

echo.
echo Xray could not be bundled automatically. The EXE will still build and can download/use core\xray.exe at runtime.
echo To bundle Xray manually, put xray.exe, geoip.dat and geosite.dat inside the core folder, then run this file again.
echo.

:xray_ready
if exist "core\xray.exe" (
  echo Xray core ready: core\xray.exe
  set "XRAY_ARGS=--add-binary core\xray.exe;core"
) else (
  echo Building without bundled Xray core.
  set "XRAY_ARGS="
)

echo [3/4] Building one-file GUI executable...
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DicodeConfigChecker ^
  --icon "assets\app.ico" ^
  %XRAY_ARGS% ^
  --add-data "assets;assets" ^
  app.py
if errorlevel 1 goto fail

echo [4/4] Preparing release asset...
if not exist "release" mkdir "release"
copy /Y "dist\DicodeConfigChecker.exe" "release\DicodeConfigChecker-v%APP_VERSION%-windows.exe" >nul
if errorlevel 1 goto fail

echo Done.
echo Output: dist\DicodeConfigChecker.exe
echo Release asset: release\DicodeConfigChecker-v%APP_VERSION%-windows.exe
echo.
pause
exit /b 0

:download_xray
%PYTHON_CMD% engine.py --download-xray-only
exit /b %errorlevel%

:fail
echo.
echo Build failed.
pause
exit /b 1
