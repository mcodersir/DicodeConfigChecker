@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

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

echo [1/4] Installing build requirements...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 goto fail
%PYTHON_CMD% -m pip install -r requirements-build.txt
if errorlevel 1 goto fail

echo [2/4] Downloading latest Xray-core before building...
%PYTHON_CMD% engine.py --download-xray-only
if errorlevel 1 goto fail
if not exist "core\xray.exe" (
  echo Xray was not prepared at core\xray.exe
  goto fail
)

echo [3/4] Building one-file GUI executable...
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DicodeConfigChecker ^
  --icon "assets\app.ico" ^
  --add-binary "core\xray.exe;core" ^
  --add-data "assets;assets" ^
  app.py
if errorlevel 1 goto fail

echo [4/4] Done.
echo Output: dist\DicodeConfigChecker.exe
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
