"""Writable cross-platform runtime paths for desktop packages."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from types import ModuleType

APP_DIR_NAME = "DicodeConfigChecker"
_RUNTIME_FILES = {
    "ENV_FILE": ".env",
    "CHANNELS_FILE": "channels.txt",
    "STAGE1_FILE": "all_configs_stage1.txt",
    "STAGE1_META_FILE": "stage1_report.json",
    "SUB_FILE": "sub.txt",
    "SUB_BASE64_FILE": "sub_base64.txt",
    "PROXY_FILE": "proxy.txt",
    "PROXY_BASE64_FILE": "proxy_base64.txt",
    "ALIVE_REPORT_FILE": "alive_report.txt",
    "PROXY_REPORT_FILE": "proxy_report.txt",
    "REPORT_FILE": "report.json",
    "LOG_FILE": "run_log.txt",
}


def application_data_dir(
    system: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    values = os.environ if env is None else env
    override = values.get("DICODE_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    current_system = (system or platform.system()).lower()
    user_home = Path.home() if home is None else home
    if current_system.startswith("win"):
        root = values.get("LOCALAPPDATA") or values.get("APPDATA")
        return (Path(root) if root else user_home / "AppData" / "Local") / APP_DIR_NAME
    if current_system == "darwin":
        return user_home / "Library" / "Application Support" / APP_DIR_NAME
    root = values.get("XDG_DATA_HOME", "").strip()
    return (Path(root) if root else user_home / ".local" / "share") / APP_DIR_NAME


def _copy_if_missing(source: Path, target: Path) -> None:
    if target.exists() or not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source, target)
    except OSError:
        # A stale or read-only portable directory must never block startup.
        pass


def _reload_environment(engine: ModuleType) -> None:
    loaded = engine.load_env_file()
    engine.ENV = loaded
    engine.PER_CHANNEL_LIMIT = engine.env_int("PER_CHANNEL_LIMIT", engine.PER_CHANNEL_LIMIT)
    engine.MAIN_CHANNEL_LIMIT = engine.env_int("MAIN_CHANNEL_LIMIT", engine.MAIN_CHANNEL_LIMIT)
    engine.FETCH_WORKERS = engine.env_int("FETCH_WORKERS", engine.FETCH_WORKERS)
    engine.FETCH_TIMEOUT = engine.env_float("FETCH_TIMEOUT", engine.FETCH_TIMEOUT)
    engine.TEST_MODE = engine.env_str("TEST_MODE", engine.TEST_MODE).lower()
    engine.XRAY_PATH = engine.env_str("XRAY_PATH", engine.XRAY_PATH)
    engine.XRAY_STARTUP_WAIT = engine.env_float("XRAY_STARTUP_WAIT", engine.XRAY_STARTUP_WAIT)
    engine.XRAY_PROCESS_TIMEOUT = engine.env_float("XRAY_PROCESS_TIMEOUT", engine.XRAY_PROCESS_TIMEOUT)
    engine.CHECK_URL = engine.env_str("CHECK_URL", engine.CHECK_URL)
    engine.PING_WORKERS = engine.env_int("PING_WORKERS", engine.PING_WORKERS)
    engine.TCP_FALLBACK_WORKERS = engine.env_int("TCP_FALLBACK_WORKERS", engine.TCP_FALLBACK_WORKERS)
    engine.SOCKET_TIMEOUT = engine.env_float("SOCKET_TIMEOUT", engine.SOCKET_TIMEOUT)
    engine.TCP_TIMEOUT = engine.env_float("TCP_TIMEOUT", engine.TCP_TIMEOUT)
    engine.PING_ATTEMPTS = engine.env_int("PING_ATTEMPTS", engine.PING_ATTEMPTS)
    engine.MIN_SUCCESS = engine.env_int("MIN_SUCCESS", engine.MIN_SUCCESS)
    engine.ATTEMPT_GAP_SECONDS = engine.env_float("ATTEMPT_GAP_SECONDS", engine.ATTEMPT_GAP_SECONDS)
    engine.SUB_TAG_PREFIX = engine.env_str("SUB_TAG_PREFIX", engine.SUB_TAG_PREFIX)
    engine.RENAME_CONFIG_NAMES = engine.env_bool("RENAME_CONFIG_NAMES", engine.RENAME_CONFIG_NAMES)
    engine.CHECK_V2RAY_CONFIGS = engine.env_bool("CHECK_V2RAY_CONFIGS", engine.CHECK_V2RAY_CONFIGS)
    engine.CHECK_TELEGRAM_PROXIES = engine.env_bool("CHECK_TELEGRAM_PROXIES", engine.CHECK_TELEGRAM_PROXIES)


def configure_engine_paths(engine: ModuleType) -> Path:
    """Move mutable files out of the executable directory and configure engine."""
    legacy_root = Path(engine.ROOT)
    data_root = application_data_dir()
    data_root.mkdir(parents=True, exist_ok=True)

    for attribute, filename in _RUNTIME_FILES.items():
        target = data_root / filename
        _copy_if_missing(legacy_root / filename, target)
        setattr(engine, attribute, target)

    engine.ROOT = data_root
    engine.CORE_DIR = data_root / "core"
    engine.CORE_DIR.mkdir(parents=True, exist_ok=True)
    _reload_environment(engine)
    return data_root
