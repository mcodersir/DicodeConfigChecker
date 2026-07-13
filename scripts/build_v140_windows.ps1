$ErrorActionPreference = "Stop"
python engine.py --download-xray-only
if (-not (Test-Path "core\xray.exe")) { throw "xray.exe missing" }
if (-not (Test-Path "core\geoip.dat")) { throw "geoip.dat missing" }
if (-not (Test-Path "core\geosite.dat")) { throw "geosite.dat missing" }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DicodeConfigChecker --icon assets\app.ico --add-data "assets;assets" --add-binary "core\xray.exe;core" --add-data "core\geoip.dat;core" --add-data "core\geosite.dat;core"
