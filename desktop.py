#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform launcher for Dicode Config Checker 1.1.0."""
from __future__ import annotations

import os
import platform
import time
from typing import Callable

VERSION = "1.4.0"
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

if platform.system().lower().startswith("win"):
    os.environ.setdefault("XRAY_PATH", "core/xray.exe")
else:
    os.environ.setdefault("XRAY_PATH", "core/xray")

import engine  # noqa: E402

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

app.APP_VERSION = VERSION
app.APP_TITLE = "Dicode Config Checker"


def main() -> int:
    return app.main()


if __name__ == "__main__":
    raise SystemExit(main())
