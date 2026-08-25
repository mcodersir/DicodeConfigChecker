#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform launcher for Dicode Config Checker."""
from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path
from typing import Callable

VERSION = "1.5.1"
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

if platform.system().lower().startswith("win"):
    os.environ.setdefault("XRAY_PATH", "core/xray.exe")
else:
    os.environ.setdefault("XRAY_PATH", "core/xray")

import engine  # noqa: E402
from runtime_paths import configure_engine_paths  # noqa: E402

configure_engine_paths(engine)
engine.VERSION = VERSION
engine.APP_NAME = "Dicode Config Checker"
_original_fetch_url: Callable[[str], str] = engine.fetch_url


def _resilient_fetch_url(url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            data = _original_fetch_url(url)
            if data.strip():
                return data
            raise RuntimeError("empty response")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.35 * (attempt + 1))
    assert last_error is not None
    raise last_error


engine.fetch_url = _resilient_fetch_url

import app  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app.APP_VERSION = VERSION
app.APP_TITLE = "Dicode Config Checker"


def _resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def _load_vazirmatn(application: QApplication) -> str:
    candidates = (
        _resource_path("assets", "fonts", "Vazirmatn-Regular.ttf"),
        _resource_path("assets", "Vazirmatn-Regular.ttf"),
    )
    for font_path in candidates:
        if not font_path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family = families[0]
            application.setFont(QFont(family, 10))
            return family
    for family in ("Vazirmatn", "Vazir", "Noto Sans Arabic", "Segoe UI"):
        if family in QFontDatabase.families():
            application.setFont(QFont(family, 10))
            return family
    return application.font().family()


def main() -> int:
    app.set_windows_app_id()
    application = QApplication(sys.argv)
    application.setApplicationName(app.APP_TITLE)
    application.setApplicationVersion(VERSION)
    application.setLayoutDirection(Qt.RightToLeft)
    _load_vazirmatn(application)

    icon_path = _resource_path("assets", "app.ico")
    if icon_path.exists():
        application.setWindowIcon(QIcon(str(icon_path)))

    window = app.MainWindow()
    window.setLayoutDirection(Qt.RightToLeft)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
