#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import base64
import ctypes
import html as html_lib
import concurrent.futures
from concurrent.futures import FIRST_COMPLETED, wait
import json
import os
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime
from collections import deque
from pathlib import Path
from threading import Event
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QSettings
from PySide6.QtGui import QIcon, QPixmap, QFont, QAction, QPainter, QPen, QBrush, QColor, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

import engine
import subscription_publisher

APP_TITLE = "Dicode Config Checker"
APP_VERSION = engine.VERSION
GITHUB_TOKEN_CREATE_URL = "https://github.com/settings/tokens/new?scopes=public_repo&description=DicodeConfigChecker%20Personal%20Subscription"


@dataclass
class RunSettings:
    per_channel_limit: int
    main_channel_limit: int
    priority1_channels_text: str
    priority2_channels_text: str
    fetch_workers: int
    fetch_timeout: float
    test_mode: str
    ping_attempts: int
    min_success: int
    ping_workers: int
    tcp_timeout: float
    socket_timeout: float
    xray_startup_wait: float
    xray_process_timeout: float
    check_url: str
    sub_tag_prefix: str
    rename_config_names: bool
    check_v2ray_configs: bool
    check_telegram_proxies: bool
    prefilter_enabled: bool
    prefilter_workers: int


class CheckerWorker(QThread):
    log_line = Signal(str)
    stage_text = Signal(str)
    progress = Signal(int, int)
    counters = Signal(int, int, int, int)
    ask_disconnect = Signal()
    paused = Signal()
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, settings: RunSettings) -> None:
        super().__init__()
        self.settings = settings
        self._continue_event = Event()
        self._resume_event = Event()
        self._resume_event.set()
        self._stop_requested = False
        self._abort_requested = False
        self._pause_requested = False

    def continue_after_disconnect(self) -> None:
        self._continue_event.set()

    def resume_after_pause(self) -> None:
        self._pause_requested = False
        self._resume_event.set()

    def request_stop(self) -> None:
        # Soft stop: pause after current in-flight checks and keep partial outputs.
        self._pause_requested = True
        self._resume_event.clear()

    def request_abort(self) -> None:
        self._abort_requested = True
        self._stop_requested = True
        self._pause_requested = False
        self._resume_event.set()
        self._continue_event.set()

    def emit_log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_line.emit(f"[{stamp}] {text}")

    def run(self) -> None:
        try:
            self.apply_runtime_settings()
            engine.ensure_files()
            engine.clear_old_outputs()

            # Collection must visibly start right after the user clicks the
            # first action.  Xray preparation can take a while on restricted
            # networks, so do it concurrently while Telegram previews are read.
            self.stage_text.emit("دریافت از تلگرام")
            self.emit_log("دریافت کانال‌ها فوراً شروع شد؛ Xray هم در پس‌زمینه آماده می‌شود.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as prep:
                xray_future = prep.submit(engine.ensure_xray_binary)
                self.collect_stage1()
                xray_path = xray_future.result()
            if xray_path:
                self.emit_log(f"Xray آماده است: {xray_path}")
            elif self.settings.test_mode == "xray":
                self.emit_log("Xray پیدا نشد؛ در حالت Xray-only تایید انجام نمی‌شود.")
            else:
                self.emit_log("Xray پیدا نشد؛ در حالت auto از TCP fallback استفاده می‌شود.")

            if self._abort_requested:
                return

            if self._abort_requested:
                return

            self.stage_text.emit("منتظر قطع اتصال")
            self.emit_log("مرحله دریافت تمام شد. اتصال فعلی را کامل قطع کنید، سپس ادامه را بزنید.")
            self.ask_disconnect.emit()
            self._continue_event.wait()
            if self._abort_requested:
                return

            final_report = self.test_stage2(xray_path)
            if not self._abort_requested:
                self.finished_ok.emit(final_report)
        except Exception as exc:
            try:
                engine.log("GUI FATAL: " + repr(exc))
            except Exception:
                pass
            self.failed.emit(str(exc))

    def apply_runtime_settings(self) -> None:
        s = self.settings
        engine.PER_CHANNEL_LIMIT = s.per_channel_limit
        engine.MAIN_CHANNEL_LIMIT = s.main_channel_limit
        priority_one = self.normalize_channel_text(s.priority1_channels_text)
        priority_two = self.normalize_channel_text(s.priority2_channels_text)
        engine.MAIN_CHANNELS = {(engine.normalize_channel(x) or x.replace("t.me/", "")).lower() for x in priority_one}
        engine.MAIN_CHANNEL = next(iter(engine.MAIN_CHANNELS), "persianvpnhub")
        engine.FETCH_WORKERS = s.fetch_workers
        engine.FETCH_TIMEOUT = s.fetch_timeout
        engine.TEST_MODE = s.test_mode
        engine.PING_ATTEMPTS = s.ping_attempts
        engine.MIN_SUCCESS = s.min_success
        engine.PING_WORKERS = s.ping_workers
        engine.TCP_TIMEOUT = s.tcp_timeout
        engine.SOCKET_TIMEOUT = s.socket_timeout
        engine.XRAY_STARTUP_WAIT = s.xray_startup_wait
        engine.XRAY_PROCESS_TIMEOUT = s.xray_process_timeout
        engine.CHECK_URL = s.check_url.strip() or "http://www.gstatic.com/generate_204"
        engine.SUB_TAG_PREFIX = s.sub_tag_prefix.strip() or "t.me/dicodeir"
        engine.RENAME_CONFIG_NAMES = bool(s.rename_config_names)
        engine.CHECK_V2RAY_CONFIGS = bool(s.check_v2ray_configs)
        engine.CHECK_TELEGRAM_PROXIES = bool(s.check_telegram_proxies)

        combined_lines = self.merge_priority_channels(priority_one, priority_two)
        engine.CHANNELS_FILE.write_text("\n".join(combined_lines) + "\n", encoding="utf-8")
        self.write_env_file(s)

    @staticmethod
    def normalize_channel_text(text: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in text.replace(",", "\n").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ch = engine.normalize_channel(line)
            if not ch:
                continue
            key = ch.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(f"t.me/{ch}")
        return out

    @staticmethod
    def merge_priority_channels(priority_one: list[str], priority_two: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for group in (priority_one, priority_two):
            for line in group:
                ch = engine.normalize_channel(line)
                if not ch:
                    continue
                key = ch.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(f"t.me/{ch}")
        return out

    @staticmethod
    def write_env_file(s: RunSettings) -> None:
        text = f"""# Dicode Config Checker v1 settings
PER_CHANNEL_LIMIT={s.per_channel_limit}
MAIN_CHANNEL_LIMIT={s.main_channel_limit}
MAIN_CHANNELS={",".join([engine.normalize_channel(x) or x.replace("t.me/", "") for x in CheckerWorker.normalize_channel_text(s.priority1_channels_text)])}
FETCH_WORKERS={s.fetch_workers}
FETCH_TIMEOUT={s.fetch_timeout}
TEST_MODE={s.test_mode}
AUTO_DOWNLOAD_XRAY=1
XRAY_PATH=core/xray.exe
XRAY_DOWNLOAD_TIMEOUT=90
XRAY_STARTUP_WAIT={s.xray_startup_wait}
XRAY_PROCESS_TIMEOUT={s.xray_process_timeout}
CHECK_URL={s.check_url}
PING_ATTEMPTS={s.ping_attempts}
MIN_SUCCESS={s.min_success}
PING_WORKERS={s.ping_workers}
TCP_FALLBACK_WORKERS=48
SOCKET_TIMEOUT={s.socket_timeout}
TCP_TIMEOUT={s.tcp_timeout}
ATTEMPT_GAP_SECONDS=0.12
SUB_TAG_PREFIX={s.sub_tag_prefix}
RENAME_CONFIG_NAMES={1 if s.rename_config_names else 0}
CHECK_V2RAY_CONFIGS={1 if s.check_v2ray_configs else 0}
CHECK_TELEGRAM_PROXIES={1 if s.check_telegram_proxies else 0}
WRITE_DEAD_TO_REPORT=1
"""
        engine.ENV_FILE.write_text(text, encoding="utf-8")

    def collect_stage1(self) -> dict[str, Any]:
        self.stage_text.emit("دریافت از تلگرام")
        channels = engine.read_channels()
        total = max(len(channels), 1)
        self.progress.emit(0, total)
        self.emit_log(f"کانال‌ها: {len(channels)} | رتبه دوم: {engine.PER_CHANNEL_LIMIT} | رتبه اول: {engine.MAIN_CHANNEL_LIMIT} | تعداد رتبه اول: {len(getattr(engine, 'MAIN_CHANNELS', []))}")

        results: list[dict[str, Any]] = []
        collected: list[dict[str, str]] = []
        seen: set[str] = set()
        start = time.time()
        done = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=engine.FETCH_WORKERS) as ex:
            future_map = {ex.submit(engine.fetch_channel, ch): ch for ch in channels}
            for fut in concurrent.futures.as_completed(future_map):
                if self._abort_requested:
                    break
                res = fut.result()
                results.append(res)
                done += 1
                status = "OK" if res.get("ok") else "FAIL"
                self.emit_log(f"{status} @{res['channel']} | found={res['found']} | picked={res['picked']} | {res['elapsed_ms']}ms")
                for cfg in res.get("configs", []):
                    key = engine.normalize_config_key(cfg)
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append({"source": res["channel"], "raw": cfg})
                self.progress.emit(done, total)
                self.counters.emit(0, 0, 0, 0)

        elapsed = int(time.time() - start)
        lines = [x["raw"] for x in collected]
        engine.STAGE1_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        meta = {
            "generated_at": engine.now_iso(),
            "stage": 1,
            "channels": len(channels),
            "per_channel_limit": engine.PER_CHANNEL_LIMIT,
            "priority_one_channels": sorted(getattr(engine, "MAIN_CHANNELS", [])),
            "main_channel_limit": engine.MAIN_CHANNEL_LIMIT,
            "unique_configs": len(lines),
            "elapsed_seconds": elapsed,
            "results": results,
            "collected": collected,
        }
        engine.STAGE1_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self.emit_log(f"مرحله اول تمام شد: {len(lines)} کانفیگ یکتا در all_configs_stage1.txt ذخیره شد.")
        return meta

    def tcp_prefilter(self, endpoints: list[Any]) -> tuple[list[Any], list[Any]]:
        if not self.settings.prefilter_enabled:
            return endpoints, []
        self.stage_text.emit("پیش‌فیلتر TCP")
        self.emit_log("اول TCP سریع اجرا می‌شود تا تست Xray روی سرورهای مرده انجام نشود.")
        total = max(len(endpoints), 1)
        kept: list[Any] = []
        rejected: list[Any] = []
        done = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.settings.prefilter_workers) as ex:
            futs = {ex.submit(engine.tcp_connect_delay_ms, ep.host, ep.port, min(engine.TCP_TIMEOUT, 2.2)): ep for ep in endpoints}
            for fut in concurrent.futures.as_completed(futs):
                ep = futs[fut]
                ms, _ = fut.result()
                if ms is not None:
                    kept.append(ep)
                else:
                    rejected.append(ep)
                done += 1
                self.progress.emit(done, total)
                if done % 10 == 0 or done == total:
                    self.emit_log(f"Prefilter {done}/{total} | قابل تست={len(kept)} | رد شده={len(rejected)}")
        return kept, rejected

    def write_partial_outputs(self, results: list[Any], unsupported: list[str], elapsed: int, xray_path: Optional[Path]) -> dict[str, Any]:
        alive = sorted([r for r in results if r.ok], key=lambda r: r.ping_ms if r.ping_ms is not None else 999999)
        dead = [r for r in results if not r.ok]
        alive_configs = [r for r in alive if r.kind != "mtproto"]
        alive_proxies = [r for r in alive if r.kind == "mtproto"]
        dead_configs = [r for r in dead if r.kind != "mtproto"]
        dead_proxies = [r for r in dead if r.kind == "mtproto"]

        renamed_config_items: list[tuple[int, Any, str, str]] = []
        for idx, r in enumerate(alive_configs, 1):
            if engine.RENAME_CONFIG_NAMES:
                display_name = f"{engine.SUB_TAG_PREFIX}-{idx}"
                output_raw = engine.set_config_display_name(r.raw, display_name)
            else:
                display_name = engine.get_config_display_name(r.raw) or f"original-{idx}"
                output_raw = r.raw
            renamed_config_items.append((idx, r, output_raw, display_name))

        sub_lines = [x[2] for x in renamed_config_items]
        proxy_lines = [r.raw for r in alive_proxies]
        engine.SUB_FILE.write_text("\n".join(sub_lines) + ("\n" if sub_lines else ""), encoding="utf-8")
        engine.SUB_BASE64_FILE.write_text(base64.b64encode(("\n".join(sub_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")
        engine.PROXY_FILE.write_text("\n".join(proxy_lines) + ("\n" if proxy_lines else ""), encoding="utf-8")
        engine.PROXY_BASE64_FILE.write_text(base64.b64encode(("\n".join(proxy_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")
        engine.write_reports(renamed_config_items, alive_proxies, dead_configs, dead_proxies, unsupported, elapsed, xray_path)

        full = {
            "generated_at": engine.now_iso(),
            "version": APP_VERSION,
            "mode": "gui-two-stage-xray-real-delay",
            "settings": {
                "per_channel_limit": engine.PER_CHANNEL_LIMIT,
                "main_channel_limit": engine.MAIN_CHANNEL_LIMIT,
                "priority_one_channels": sorted(getattr(engine, "MAIN_CHANNELS", [])),
                "rename_config_names": engine.RENAME_CONFIG_NAMES,
                "check_v2ray_configs": self.settings.check_v2ray_configs,
                "check_telegram_proxies": self.settings.check_telegram_proxies,
                "sub_tag_prefix": engine.SUB_TAG_PREFIX,
                "test_mode": engine.TEST_MODE,
                "prefilter_enabled": self.settings.prefilter_enabled,
                "xray_path": str(xray_path) if xray_path else None,
                "check_url": engine.CHECK_URL,
                "attempts": engine.PING_ATTEMPTS,
                "min_success": engine.MIN_SUCCESS,
                "ping_workers": engine.PING_WORKERS,
            },
            "stats": {
                "alive_total": len(alive),
                "dead_total": len(dead),
                "alive_configs": len(alive_configs),
                "alive_telegram_proxies": len(alive_proxies),
                "dead_configs": len(dead_configs),
                "dead_telegram_proxies": len(dead_proxies),
                "unsupported": len(unsupported),
                "elapsed_seconds": elapsed,
            },
            "alive_configs": [{**asdict(r), "subscription_raw": renamed_raw, "subscription_name": display_name} for _, r, renamed_raw, display_name in renamed_config_items],
            "alive_telegram_proxies": [asdict(r) for r in alive_proxies],
            "dead_configs": [asdict(r) for r in dead_configs] if engine.WRITE_DEAD_TO_REPORT else [],
            "dead_telegram_proxies": [asdict(r) for r in dead_proxies] if engine.WRITE_DEAD_TO_REPORT else [],
            "unsupported": unsupported if engine.WRITE_DEAD_TO_REPORT else [],
        }
        engine.REPORT_FILE.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
        self.counters.emit(len(alive_configs), len(alive_proxies), len(dead), len(unsupported))
        return full

    def test_stage2(self, xray_path: Optional[Path]) -> dict[str, Any]:
        self.stage_text.emit("تست واقعی")
        items = engine.read_stage1_configs()
        endpoints: list[Any] = []
        unsupported: list[str] = []

        skipped_configs: list[str] = []
        skipped_proxies: list[str] = []
        for item in items:
            ep = engine.parse_endpoint(item["raw"], item.get("source", "stage1"))
            if ep:
                if ep.kind == "mtproto" and not self.settings.check_telegram_proxies:
                    skipped_proxies.append(item["raw"])
                    continue
                if ep.kind != "mtproto" and not self.settings.check_v2ray_configs:
                    skipped_configs.append(item["raw"])
                    continue
                endpoints.append(ep)
            else:
                unsupported.append(item["raw"])

        if skipped_configs:
            self.emit_log(f"INFO بررسی کانفیگ خاموش است؛ {len(skipped_configs)} کانفیگ رد شد.")
        if skipped_proxies:
            self.emit_log(f"INFO بررسی پروکسی خاموش است؛ {len(skipped_proxies)} پروکسی تلگرام رد شد.")
        self.emit_log(f"INFO خوانده‌شده: {len(items)} | قابل تست: {len(endpoints)} | پشتیبانی‌نشده: {len(unsupported)}")
        endpoints, prefiltered_dead = self.tcp_prefilter(endpoints)

        total = max(len(endpoints), 1)
        self.progress.emit(0, total)
        results: list[Any] = [
            engine.TestResult(
                raw=ep.raw,
                source=ep.source,
                kind=ep.kind,
                protocol=ep.protocol,
                host=ep.host,
                port=ep.port,
                ok=False,
                ping_ms=None,
                min_ms=None,
                avg_ms=None,
                attempts=1,
                success_count=0,
                samples_ms=[],
                tester="tcp-prefilter",
                error="tcp_prefilter_failed",
            )
            for ep in prefiltered_dead
        ]
        done = 0
        start = time.time()
        pending = deque(endpoints)
        running: dict[Any, Any] = {}
        workers = max(1, engine.PING_WORKERS)
        pause_announced = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            while pending or running:
                if self._abort_requested:
                    self.emit_log("ERR تست از ابتدا ریست شد؛ خروجی‌های موقت حفظ نشدند.")
                    break

                if self._pause_requested:
                    if not pause_announced:
                        pause_announced = True
                        self.stage_text.emit("توقف موقت")
                        self.emit_log("INFO توقف موقت فعال شد؛ تست‌های در حال اجرا تمام می‌شوند و تست جدید شروع نمی‌شود.")
                        engine.cleanup_xray_processes()
                        elapsed = int(time.time() - start)
                        self.write_partial_outputs(results, unsupported, elapsed, xray_path)
                        self.paused.emit()
                    # keep collecting finished in-flight tasks; submit nothing new.
                else:
                    if pause_announced:
                        pause_announced = False
                        self.stage_text.emit("ادامه تست واقعی")
                        self.emit_log("INFO ادامه تست از همان نقطه شروع شد.")
                    while pending and len(running) < workers:
                        ep = pending.popleft()
                        fut = ex.submit(engine.repeated_test, ep, xray_path)
                        running[fut] = ep

                if not running:
                    self._resume_event.wait(0.15)
                    continue

                done_set, _ = wait(list(running.keys()), timeout=0.25, return_when=FIRST_COMPLETED)
                if not done_set:
                    continue

                for fut in done_set:
                    ep = running.pop(fut, None)
                    try:
                        res = fut.result()
                    except Exception as exc:
                        if ep is None:
                            continue
                        res = engine.TestResult(ep.raw, ep.source, ep.kind, ep.protocol, ep.host, ep.port, False, None, None, None, engine.PING_ATTEMPTS, 0, [], "internal", repr(exc))
                    results.append(res)
                    done += 1
                    if res.ok:
                        self.emit_log(f"OK {res.protocol} {res.host}:{res.port} | {engine.fmt_ms(res.ping_ms)} | {res.success_count}/{res.attempts} | {res.tester}")
                    else:
                        self.emit_log(f"FAIL {res.protocol} {res.host}:{res.port} | {res.error or 'failed'}")
                    alive_configs_live = len([r for r in results if r.ok and r.kind != "mtproto"])
                    alive_proxies_live = len([r for r in results if r.ok and r.kind == "mtproto"])
                    dead_count = len([r for r in results if not r.ok])
                    self.progress.emit(done, total)
                    self.counters.emit(alive_configs_live, alive_proxies_live, dead_count, len(unsupported))
                    if done % 5 == 0 or res.ok:
                        elapsed = int(time.time() - start)
                        self.write_partial_outputs(results, unsupported, elapsed, xray_path)

        elapsed = int(time.time() - start)
        final = self.write_partial_outputs(results, unsupported, elapsed, xray_path)
        stats = final.get("stats", {})
        self.emit_log(f"OK تمام شد: sub.txt={stats.get('alive_configs', 0)} | proxy.txt={stats.get('alive_telegram_proxies', 0)} | dead={stats.get('dead_total', 0)} | unsupported={stats.get('unsupported', 0)}")
        engine.cleanup_xray_processes()
        return final

def resource_path(*parts: str) -> Path:
    root_candidate = engine.ROOT.joinpath(*parts)
    if root_candidate.exists():
        return root_candidate
    bundle_candidate = engine.BUNDLE_DIR.joinpath(*parts)
    if bundle_candidate.exists():
        return bundle_candidate
    return root_candidate



class LogoMark(QWidget):
    def __init__(self, size: int = 44) -> None:
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QPen(QColor("#24527a"), 1.4))
        painter.setBrush(QBrush(QColor("#07101b")))
        painter.drawRoundedRect(r, 12, 12)
        inner = self.rect().adjusted(9, 9, -9, -9)
        painter.setPen(QPen(QColor("#2a9fff"), 1.2))
        painter.setBrush(QBrush(QColor("#0d2134")))
        painter.drawRoundedRect(inner, 8, 8)
        w = self.width()
        h = self.height()
        bolt = QPolygonF([
            QPointF(w * 0.55, h * 0.18),
            QPointF(w * 0.34, h * 0.52),
            QPointF(w * 0.50, h * 0.52),
            QPointF(w * 0.43, h * 0.82),
            QPointF(w * 0.68, h * 0.44),
            QPointF(w * 0.51, h * 0.44),
        ])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#68e8ff")))
        painter.drawPolygon(bolt)

class IconButton(QPushButton):
    def __init__(self, text: str, icon_name: str = "", primary: bool = False) -> None:
        super().__init__(text)
        if icon_name:
            icon_path = resource_path("assets", f"{icon_name}.svg")
            if icon_path.exists():
                self.setIcon(QIcon(str(icon_path)))
                self.setIconSize(QSize(18, 18))
        if primary:
            self.setObjectName("PrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)


class HomeStepCard(QFrame):
    """A compact stateful operation card for the home screen."""

    def __init__(self, number: int, title: str, subtitle: str, button_text: str, icon_name: str) -> None:
        super().__init__()
        self.setObjectName("HomeStepCard")
        self.setProperty("state", "idle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(9)
        header = QHBoxLayout()
        header.setSpacing(10)
        badge = QLabel(str(number))
        badge.setObjectName("StepNumber")
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignCenter)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("StepTitle")
        self.title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.state_label = QLabel("آماده")
        self.state_label.setObjectName("StepState")
        self.state_label.setAlignment(Qt.AlignCenter)
        header.addWidget(badge)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.state_label)
        layout.addLayout(header)
        hint = QLabel(subtitle)
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        hint.setLayoutDirection(Qt.RightToLeft)
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(hint)
        self.button = IconButton(button_text, icon_name, primary=True)
        layout.addWidget(self.button)

    def set_state(self, state: str, label: str) -> None:
        self.setProperty("state", state)
        self.state_label.setText(label)
        self.style().unpolish(self)
        self.style().polish(self)


class NavButton(QToolButton):
    def __init__(self, text: str, icon_name: str, index: int) -> None:
        super().__init__()
        self.index = index
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        self.setIconSize(QSize(20, 20))
        self.setMinimumHeight(44)


class StatCard(QFrame):
    def __init__(self, title: str, icon_name: str) -> None:
        super().__init__()
        self.setObjectName("StatCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignVCenter)
        icon = QLabel()
        icon.setObjectName("CardIcon")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignCenter)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            icon.setPixmap(QPixmap(str(icon_path)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        text_box = QVBoxLayout()
        self.value = QLabel("0")
        self.value.setObjectName("CardValue")
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label = QLabel(title)
        label.setObjectName("CardLabel")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        text_box.setAlignment(Qt.AlignVCenter)
        text_box.addWidget(self.value)
        text_box.addWidget(label)
        layout.addWidget(icon)
        layout.addLayout(text_box, 1)

    def set_value(self, value: int | str) -> None:
        self.value.setText(str(value))



class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[CheckerWorker] = None
        self.app_settings = QSettings("Dicode", "DicodeConfigChecker")
        self.compact_nav = False
        self.sidebar_collapsed = False
        self._drag_position = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.setMinimumSize(920, 620)
        self.resize(1220, 760)
        icon_path = resource_path("assets", "app.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.build_ui()
        self.load_initial_values()
        self.apply_style()
        self.update_channel_count()
        QTimer.singleShot(80, self.apply_responsive_mode)

    def build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.root = root
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        self.root_layout = root_layout
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.topbar = QFrame()
        self.topbar.setObjectName("TopBar")
        top = QHBoxLayout(self.topbar)
        top.setContentsMargins(14, 10, 12, 10)
        top.setSpacing(10)

        self.btn_nav_toggle = QToolButton()
        self.btn_nav_toggle.setObjectName("TopIconButton")
        self.btn_nav_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_nav_toggle.setToolTip("باز و بسته کردن منوی کناری")
        icon_path = resource_path("assets", "list.svg")
        if icon_path.exists():
            self.btn_nav_toggle.setIcon(QIcon(str(icon_path)))
        self.btn_nav_toggle.setIconSize(QSize(18, 18))
        self.btn_nav_toggle.setFixedSize(42, 42)
        self.btn_nav_toggle.clicked.connect(self.toggle_sidebar)
        top.addWidget(self.btn_nav_toggle)

        self.header_logo = LogoMark(42)
        top.addWidget(self.header_logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.title_label = QLabel("Dicode Config Checker")
        self.title_label.setObjectName("Title")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle_label = QLabel("اسکن کانال‌ها، تست کیفیت اتصال و ساخت خروجی‌های sub.txt / proxy.txt")
        self.subtitle_label.setObjectName("Subtitle")
        self.subtitle_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.subtitle_label.setLayoutDirection(Qt.RightToLeft)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        top.addLayout(title_box, 1)

        self.btn_minimize = QToolButton()
        self.btn_minimize.setObjectName("WindowButton")
        self.btn_minimize.setText("—")
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize = QToolButton()
        self.btn_maximize.setObjectName("WindowButton")
        self.btn_maximize.setText("□")
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.btn_close = QToolButton()
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setText("×")
        self.btn_close.clicked.connect(self.close)
        for b in (self.btn_minimize, self.btn_maximize, self.btn_close):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(38, 38)
            top.addWidget(b)
        root_layout.addWidget(self.topbar)

        body = QHBoxLayout()
        body.setSpacing(10)
        root_layout.addLayout(body, 1)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(216)
        nav_layout = QVBoxLayout(self.sidebar)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(8)

        self.sidebar_caption = QLabel("منوی ابزار")
        self.sidebar_caption.setObjectName("SidebarCaption")
        self.sidebar_caption.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        nav_layout.addWidget(self.sidebar_caption)

        self.nav_dashboard = NavButton("داشبورد", "dashboard", 0)
        self.nav_settings = NavButton("تنظیمات", "sliders", 1)
        self.nav_channels = NavButton("کانال‌ها", "list", 2)
        self.nav_configs = NavButton("کانفیگ‌ها", "check", 3)
        self.nav_proxies = NavButton("پروکسی‌ها", "bolt", 4)
        self.nav_dashboard.setChecked(True)
        self.nav_buttons = [self.nav_dashboard, self.nav_settings, self.nav_channels, self.nav_configs, self.nav_proxies]
        for btn in self.nav_buttons:
            nav_layout.addWidget(btn)
            btn.clicked.connect(lambda checked=False, b=btn: self.switch_page(b.index))

        nav_layout.addStretch(1)
        self.btn_open_side = IconButton("پوشه خروجی", "folder")
        self.btn_open_side.clicked.connect(self.open_output_folder)
        nav_layout.addWidget(self.btn_open_side)
        body.addWidget(self.sidebar)

        self.content_panel = QFrame()
        self.content_panel.setObjectName("ContentPanel")
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(12)
        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages, 1)
        body.addWidget(self.content_panel, 1)

        self.build_dashboard_page()
        self.build_settings_page()
        self.build_channels_page()
        self.build_output_pages()

    def build_dashboard_page(self) -> None:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)

        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(10)
        self.card_alive_configs = StatCard("کانفیگ سالم", "check")
        self.card_alive_proxies = StatCard("پروکسی سالم", "bolt")
        self.card_dead = StatCard("ناموفق", "x")
        self.card_unsupported = StatCard("پشتیبانی‌نشده", "alert")
        self.stat_cards = [self.card_alive_configs, self.card_alive_proxies, self.card_dead, self.card_unsupported]
        for i, card in enumerate(self.stat_cards):
            self.cards_grid.addWidget(card, 0, i)
        page_layout.addLayout(self.cards_grid)

        progress_panel = QFrame()
        progress_panel.setObjectName("Panel")
        pp = QVBoxLayout(progress_panel)
        pp.setContentsMargins(14, 12, 14, 12)
        pp.setSpacing(10)
        top = QHBoxLayout()
        self.progress_meta = QLabel("برای شروع روی دکمه شروع بزن")
        self.progress_meta.setObjectName("Muted")
        self.progress_meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.progress_meta.setLayoutDirection(Qt.RightToLeft)
        self.progress_title = QLabel("وضعیت اجرا")
        self.progress_title.setObjectName("SectionTitle")
        self.progress_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.progress_meta)
        top.addStretch(1)
        top.addWidget(self.progress_title)
        pp.addLayout(top)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value", self)
        self.progress_anim.setDuration(120)
        self.progress_anim.setEasingCurve(QEasingCurve.OutCubic)
        pp.addWidget(self.progress_bar)
        page_layout.addWidget(progress_panel)

        steps = QHBoxLayout()
        steps.setSpacing(10)
        self.step_collect = HomeStepCard(
            1, "دریافت از کانال ها", "با اتصال فعلی، کانفیگ ها و پروکسی های عمومی را جمع آوری می کند.", "شروع دریافت", "play"
        )
        self.step_test = HomeStepCard(
            2, "تست واقعی و ساخت خروجی", "بعد از قطع اتصال فعلی، موارد جمع آوری شده را با اینترنت خودت بررسی می کند.", "شروع تست واقعی", "next"
        )
        self.step_test.button.setEnabled(False)
        steps.addWidget(self.step_collect, 1)
        steps.addWidget(self.step_test, 1)
        page_layout.addLayout(steps)

        utility_actions = QHBoxLayout()
        utility_actions.setSpacing(8)
        self.btn_reset_run = IconButton("شروع دوباره", "reset")
        self.btn_open = IconButton("پوشه خروجی", "folder")
        utility_actions.addWidget(self.btn_open)
        utility_actions.addWidget(self.btn_reset_run)
        utility_actions.addStretch(1)
        page_layout.addLayout(utility_actions)

        log_panel = QFrame()
        log_panel.setObjectName("Panel")
        lp = QVBoxLayout(log_panel)
        lp.setContentsMargins(14, 12, 14, 12)
        lp.setSpacing(10)
        log_header = QHBoxLayout()
        self.btn_clear_log = IconButton("پاک کردن", "trash")
        self.btn_clear_log.clicked.connect(lambda: self.log_box.clear())
        log_title = QLabel("لاگ زنده")
        log_title.setObjectName("SectionTitle")
        log_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        log_header.addWidget(self.btn_clear_log)
        log_header.addStretch(1)
        log_header.addWidget(log_title)
        lp.addLayout(log_header)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("LogBox")
        lp.addWidget(self.log_box, 1)
        page_layout.addWidget(log_panel, 1)

        self.btn_start = self.step_collect.button
        self.btn_continue = self.step_test.button
        self.btn_stop = IconButton("توقف موقت", "stop")
        self.btn_stop.setVisible(False)

        self.btn_start.clicked.connect(self.start_run)
        self.btn_continue.clicked.connect(self.continue_run)
        self.btn_stop.clicked.connect(self.stop_run)
        self.btn_reset_run.clicked.connect(self.reset_run)
        self.btn_open.clicked.connect(self.open_output_folder)
        self.pages.addWidget(page)

    def build_settings_page(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TransparentScroll")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        scroll.setWidget(page)

        header = self.page_header("تنظیمات قبل از شروع", "تنظیمات تست، اولویت کانال‌ها، کیفیت بررسی و خروجی‌ها", "sliders")
        layout.addWidget(header)

        self.per_channel = self.spin(1, 300, 20)
        self.main_limit = self.spin(1, 1000, 30)
        self.fetch_workers = self.spin(1, 64, 10)
        self.ping_workers = self.spin(1, 32, 4)
        self.attempts = self.spin(1, 8, 2)
        self.min_success = self.spin(1, 8, 1)
        self.prefilter_workers = self.spin(1, 128, 64)
        self.test_mode = QComboBox()
        self.test_mode.addItems(["auto", "xray", "tcp"])
        self.check_url = QLineEdit("http://www.gstatic.com/generate_204")
        self.tag_prefix = QLineEdit("t.me/dicodeir")
        self.rename_names = QCheckBox("بازنویسی نام کانفیگ بعد از #")
        self.rename_names.setChecked(True)
        self.rename_names.setLayoutDirection(Qt.RightToLeft)
        self.rename_names.setToolTip("اگر خاموش باشد، نام اصلی کانفیگ‌ها حفظ می‌شود. اگر روشن باشد، متن زیر با شماره‌گذاری اعمال می‌شود.")
        self.check_configs = QCheckBox("بررسی کانفیگ‌های V2Ray/Xray و ساخت sub.txt")
        self.check_configs.setChecked(True)
        self.check_configs.setLayoutDirection(Qt.RightToLeft)
        self.check_configs.setToolTip("اگر فقط پروکسی تلگرام می‌خواهی، این گزینه را خاموش کن تا کانفیگ‌ها تست و خروجی sub.txt ساخته نشوند.")
        self.check_proxies = QCheckBox("بررسی پروکسی‌های تلگرام و ساخت proxy.txt")
        self.check_proxies.setChecked(True)
        self.check_proxies.setLayoutDirection(Qt.RightToLeft)
        self.check_proxies.setToolTip("اگر فقط کانفیگ V2Ray/Xray می‌خواهی، این گزینه را خاموش کن تا پروکسی‌های تلگرام تست نشوند.")
        self.prefilter = QCheckBox("پیش‌فیلتر سریع TCP قبل از Xray")
        self.prefilter.setChecked(True)
        self.prefilter.setLayoutDirection(Qt.RightToLeft)

        def section(title: str, subtitle: str) -> QFrame:
            wrap = QFrame()
            wrap.setObjectName("SettingsSection")
            vl = QVBoxLayout(wrap)
            vl.setContentsMargins(14, 12, 14, 14)
            vl.setSpacing(10)
            head = QLabel(title)
            head.setObjectName("SectionTitle")
            head.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            desc = QLabel(subtitle)
            desc.setObjectName("Muted")
            desc.setWordWrap(True)
            desc.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            desc.setLayoutDirection(Qt.RightToLeft)
            vl.addWidget(head)
            vl.addWidget(desc)
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(10)
            vl.addLayout(grid)
            wrap._grid = grid  # type: ignore[attr-defined]
            return wrap

        rank_box = section("اولویت کانال‌ها", "کانال‌های رتبه اول با سقف جداگانه بررسی می‌شوند؛ کانال‌های رتبه دوم با سقف عمومی.")
        rank_grid = rank_box._grid  # type: ignore[attr-defined]
        self.add_field(rank_grid, 0, 0, "تعداد کانفیگ از هر کانال رتبه دوم", self.per_channel)
        self.add_field(rank_grid, 0, 1, "تعداد کانفیگ از هر کانال رتبه اول", self.main_limit)
        layout.addWidget(rank_box)

        speed_box = section("سرعت و کیفیت تست", "پیش‌فرض سریع‌تر شده است: نمونه‌های هر سرور و معیار تایید تغییری نکرده؛ فقط چند مورد هم‌زمان‌تر بررسی می‌شوند.")
        speed_grid = speed_box._grid  # type: ignore[attr-defined]
        self.add_field(speed_grid, 0, 0, "Fetch workers", self.fetch_workers)
        self.add_field(speed_grid, 0, 1, "Ping workers", self.ping_workers)
        self.add_field(speed_grid, 1, 0, "Prefilter workers", self.prefilter_workers)
        self.add_field(speed_grid, 1, 1, "حالت تست", self.test_mode)
        self.add_field(speed_grid, 2, 0, "تعداد تلاش", self.attempts)
        self.add_field(speed_grid, 2, 1, "حداقل موفقیت", self.min_success)
        layout.addWidget(speed_box)

        output_box = section("خروجی و نام‌گذاری", "نام کانفیگ‌ها را می‌توان حفظ کرد یا با متن دلخواه و شماره‌گذاری جایگزین کرد.")
        output_grid = output_box._grid  # type: ignore[attr-defined]
        self.add_field(output_grid, 0, 0, "متن نام کانفیگ", self.tag_prefix)
        self.add_field(output_grid, 0, 1, "URL تست", self.check_url)
        opt = QFrame()
        opt.setObjectName("OptionsBox")
        opt_l = QVBoxLayout(opt)
        opt_l.setContentsMargins(12, 10, 12, 10)
        opt_l.setSpacing(10)
        opt_l.addWidget(self.rename_names)
        opt_l.addWidget(self.check_configs)
        opt_l.addWidget(self.check_proxies)
        opt_l.addWidget(self.prefilter)
        output_grid.addWidget(opt, 1, 0, 1, 2)
        layout.addWidget(output_box)

        subscription_box = section("ساب اختصاصی GitHub", "بدون نیاز به آشنایی با GitHub: سه قدم زیر را انجام بده؛ پس از هر تست، sub.txt و proxy.txt سالم خودکار به‌روز می‌شوند.")
        subscription_grid = subscription_box._grid  # type: ignore[attr-defined]
        subscription_steps = QLabel("۱. روی «ساخت توکن» بزن و وارد GitHub شو.\n۲. در صفحه بازشده فقط public_repo را انتخاب‌شده نگه دار، پایین صفحه Generate token را بزن و آن را کپی کن.\n۳. توکن را اینجا بچسبان و «ذخیره و فعال‌سازی» را بزن.")
        subscription_steps.setObjectName("Muted")
        subscription_steps.setWordWrap(True)
        subscription_steps.setLayoutDirection(Qt.RightToLeft)
        self.btn_open_token_page = IconButton("۱. ساخت توکن در GitHub", "open")
        self.btn_open_token_page.clicked.connect(self.open_github_token_page)
        self.github_token = QLineEdit()
        self.github_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.github_token.setPlaceholderText("ghp_... (Classic PAT با public_repo)")
        self.github_token.setToolTip("برای ساخت اولین ریپازیتوری عمومی، یک Classic PAT با scope=public_repo بساز. توکن فقط در تنظیمات محلی همین دستگاه ذخیره و مستقیم به GitHub ارسال می شود.")
        self.subscription_repo = QLineEdit()
        self.subscription_repo.setReadOnly(True)
        self.subscription_repo.setPlaceholderText("پس از اولین انتشار ساخته می شود")
        self.subscription_sub_url = QLineEdit(); self.subscription_sub_url.setReadOnly(True)
        self.subscription_proxy_url = QLineEdit(); self.subscription_proxy_url.setReadOnly(True)
        self.btn_save_subscription = IconButton("ذخیره و فعال سازی ساب", "save", primary=True)
        self.btn_save_subscription.clicked.connect(self.save_subscription_settings)
        subscription_grid.addWidget(subscription_steps, 0, 0, 1, 2)
        subscription_grid.addWidget(self.btn_open_token_page, 1, 0, 1, 2)
        self.add_field(subscription_grid, 2, 0, "۲. GitHub Classic PAT (public_repo)", self.github_token, 2)
        subscription_grid.addWidget(self.btn_save_subscription, 3, 0, 1, 2)
        self.add_field(subscription_grid, 4, 0, "ریپازیتوری عمومی ساب", self.subscription_repo, 2)
        self.add_field(subscription_grid, 5, 0, "لینک sub.txt", self.subscription_sub_url, 2)
        self.add_field(subscription_grid, 6, 0, "لینک proxy.txt", self.subscription_proxy_url, 2)
        layout.addWidget(subscription_box)

        reset_wrap = QFrame()
        reset_wrap.setObjectName("ResetBox")
        reset_l = QHBoxLayout(reset_wrap)
        reset_l.setContentsMargins(12, 10, 12, 10)
        reset_l.setSpacing(10)
        self.btn_reset_settings = IconButton("ریست تنظیمات", "reset")
        self.btn_reset_settings.clicked.connect(self.reset_settings)
        reset_hint = QLabel("بازگردانی تنظیمات تست به مقادیر پیشنهادی نسخه 1.0.1")
        reset_hint.setObjectName("Muted")
        reset_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        reset_hint.setLayoutDirection(Qt.RightToLeft)
        reset_l.addWidget(self.btn_reset_settings)
        reset_l.addStretch(1)
        reset_l.addWidget(reset_hint)
        layout.addWidget(reset_wrap)

        hint = QLabel("پیشنهاد تست: حالت auto، پیش‌فیلتر روشن، Ping workers روی 4، تعداد تلاش 2. اگر کیفیت مهم‌تر از زمان است، تلاش را 3 یا 4 کن.")
        hint.setObjectName("Hint")
        hint.setLayoutDirection(Qt.RightToLeft)
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.attempts.valueChanged.connect(self.fix_min_success)
        self.rename_names.toggled.connect(self.tag_prefix.setEnabled)
        self.tag_prefix.setEnabled(self.rename_names.isChecked())
        self.pages.addWidget(scroll)

    def build_channels_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        header = self.page_header("اولویت کانال‌ها", "کانال‌های رتبه اول با سقف رتبه اول و کانال‌های رتبه دوم با سقف عمومی بررسی می‌شوند.", "list")
        layout.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName("Panel")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(14, 12, 14, 12)
        tb.setSpacing(10)
        self.btn_load_file = IconButton("واردکردن فایل", "import")
        self.btn_default = IconButton("پیش‌فرض", "reset")
        self.btn_dedupe = IconButton("پاکسازی تکراری", "clean")
        self.btn_save_channels = IconButton("ذخیره", "save", primary=True)
        self.channel_count = QLabel("0 کانال")
        self.channel_count.setObjectName("StagePill")
        self.channel_count.setAlignment(Qt.AlignCenter)
        tb.addWidget(self.btn_load_file)
        tb.addWidget(self.btn_default)
        tb.addWidget(self.btn_dedupe)
        tb.addWidget(self.btn_save_channels)
        tb.addStretch(1)
        tb.addWidget(self.channel_count)
        layout.addWidget(toolbar)

        editors = QFrame()
        editors.setObjectName("Panel")
        eg = QGridLayout(editors)
        eg.setContentsMargins(14, 14, 14, 14)
        eg.setSpacing(12)

        p1_box = QFrame(); p1_box.setObjectName("FieldBox"); p1_box.setProperty("accent", "1")
        p1_l = QVBoxLayout(p1_box); p1_l.setContentsMargins(12, 10, 12, 12); p1_l.setSpacing(8)
        p1_title = QLabel("کانال‌های رتبه اول")
        p1_title.setObjectName("SectionTitle"); p1_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        p1_hint = QLabel("برای کانال‌های مهم‌تر؛ تعدادشان از تنظیمات با سقف رتبه اول کنترل می‌شود.")
        p1_hint.setObjectName("Muted"); p1_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter); p1_hint.setLayoutDirection(Qt.RightToLeft)
        self.priority1_editor = QPlainTextEdit()
        self.priority1_editor.setObjectName("ChannelEditor")
        self.priority1_editor.setLayoutDirection(Qt.LeftToRight)
        self.priority1_editor.setPlaceholderText("مثال:\nt.me/persianvpnhub")
        self.priority1_editor.textChanged.connect(self.update_channel_count)
        p1_l.addWidget(p1_title); p1_l.addWidget(p1_hint); p1_l.addWidget(self.priority1_editor, 1)

        p2_box = QFrame(); p2_box.setObjectName("FieldBox"); p2_box.setProperty("accent", "0")
        p2_l = QVBoxLayout(p2_box); p2_l.setContentsMargins(12, 10, 12, 12); p2_l.setSpacing(8)
        p2_title = QLabel("کانال‌های رتبه دوم")
        p2_title.setObjectName("SectionTitle"); p2_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        p2_hint = QLabel("هر خط یک لینک t.me / telegram.me یا یوزرنیم ساده؛ در اختلال t.me، جایگزین خودکار انجام می‌شود.")
        p2_hint.setObjectName("Muted"); p2_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter); p2_hint.setLayoutDirection(Qt.RightToLeft)
        self.priority2_editor = QPlainTextEdit()
        self.priority2_editor.setObjectName("ChannelEditor")
        self.priority2_editor.setLayoutDirection(Qt.LeftToRight)
        self.priority2_editor.setPlaceholderText("هر خط یک کانال. مثال:\nt.me/v2rayngvpn\nConfigX2ray")
        self.priority2_editor.textChanged.connect(self.update_channel_count)
        p2_l.addWidget(p2_title); p2_l.addWidget(p2_hint); p2_l.addWidget(self.priority2_editor, 1)

        eg.addWidget(p1_box, 0, 0)
        eg.addWidget(p2_box, 0, 1)
        layout.addWidget(editors, 1)

        self.btn_save_channels.clicked.connect(self.save_channels_from_editor)
        self.btn_dedupe.clicked.connect(self.dedupe_channels)
        self.btn_default.clicked.connect(self.load_default_channels)
        self.btn_load_file.clicked.connect(self.import_channels_file)
        self.pages.addWidget(page)

    def build_output_pages(self) -> None:
        self.configs_page_index = self.pages.count()
        config_page = self.build_single_output_page(
            title="کانفیگ‌ها",
            subtitle="خروجی sub.txt اینجا نمایش داده می‌شود؛ برای استفاده سریع می‌توانی کپی کنی یا فایل را باز کنی.",
            icon_name="check",
            kind="configs",
        )
        self.pages.addWidget(config_page)

        self.proxies_page_index = self.pages.count()
        proxy_page = self.build_single_output_page(
            title="پروکسی‌ها",
            subtitle="خروجی proxy.txt جدا از کانفیگ‌ها نگهداری می‌شود و فقط وقتی گزینه بررسی پروکسی روشن باشد پر می‌شود.",
            icon_name="bolt",
            kind="proxies",
        )
        self.pages.addWidget(proxy_page)

    def build_single_output_page(self, title: str, subtitle: str, icon_name: str, kind: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self.page_header(title, subtitle, icon_name))

        toolbar = QFrame()
        toolbar.setObjectName("Panel")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(14, 12, 14, 12)
        tb.setSpacing(10)
        copy_btn = IconButton("کپی خروجی", "copy", primary=True)
        reload_btn = IconButton("بارگذاری دوباره", "reset")
        open_btn = IconButton("پوشه خروجی", "folder")
        counter = QLabel("0 خط")
        counter.setObjectName("SoftPill")
        counter.setAlignment(Qt.AlignCenter)
        tb.addWidget(open_btn)
        tb.addWidget(reload_btn)
        tb.addWidget(copy_btn)
        tb.addStretch(1)
        tb.addWidget(counter)
        layout.addWidget(toolbar)

        panel = QFrame()
        panel.setObjectName("Panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 14, 14, 14)
        box = QTextEdit()
        box.setObjectName("ResultBox")
        box.setReadOnly(True)
        box.setLayoutDirection(Qt.LeftToRight)
        box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        box.setPlaceholderText("هنوز خروجی ساخته نشده است.")
        pl.addWidget(box, 1)
        layout.addWidget(panel, 1)

        if kind == "configs":
            self.config_results = box
            self.config_count_label = counter
            copy_btn.clicked.connect(lambda: self.copy_result_box("configs"))
        else:
            self.proxy_results = box
            self.proxy_count_label = counter
            copy_btn.clicked.connect(lambda: self.copy_result_box("proxies"))
        reload_btn.clicked.connect(self.refresh_result_tabs)
        open_btn.clicked.connect(self.open_output_folder)
        return page

    def page_header(self, title: str, subtitle: str, icon_name: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PageHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignVCenter)
        texts = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("PageTitle")
        t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        s = QLabel(subtitle)
        s.setObjectName("Subtitle")
        s.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        s.setWordWrap(True)
        texts.addWidget(t)
        texts.addWidget(s)
        layout.addLayout(texts, 1)
        icon = QLabel()
        icon.setObjectName("LargeIcon")
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            icon.setPixmap(QPixmap(str(icon_path)).scaled(21, 21, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon)
        return frame

    @staticmethod
    def spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setMinimumHeight(40)
        s.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        s.setAlignment(Qt.AlignCenter)
        s.setCursor(Qt.PointingHandCursor)
        return s

    @staticmethod
    def add_field(grid: QGridLayout, row: int, col: int, label_text: str, widget: QWidget, colspan: int = 1) -> None:
        wrapper = QFrame()
        wrapper.setObjectName("FieldBox")
        wrapper.setProperty("accent", str((row + col) % 5))
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        has_fa = any("\u0600" <= ch <= "\u06ff" for ch in label_text)
        label.setLayoutDirection(Qt.RightToLeft if has_fa else Qt.LeftToRight)
        label.setAlignment((Qt.AlignRight if has_fa else Qt.AlignLeft) | Qt.AlignVCenter)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if isinstance(widget, QLineEdit):
            txt = widget.text()
            fa_value = any("\u0600" <= ch <= "\u06ff" for ch in txt)
            widget.setLayoutDirection(Qt.RightToLeft if fa_value else Qt.LeftToRight)
            widget.setAlignment((Qt.AlignRight if fa_value else Qt.AlignLeft) | Qt.AlignVCenter)
        elif isinstance(widget, QComboBox):
            widget.setLayoutDirection(Qt.LeftToRight)
        else:
            widget.setLayoutDirection(Qt.RightToLeft)
        lay.addWidget(label)
        lay.addWidget(widget)
        grid.addWidget(wrapper, row, col, 1, colspan)

    def switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        if page is not None:
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(100)
            anim.setStartValue(0.9)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
            self._page_anim = anim
            anim.start()
        for btn in getattr(self, "nav_buttons", (self.nav_dashboard, self.nav_settings, self.nav_channels)):
            btn.setChecked(btn.index == index)

    def fix_min_success(self) -> None:
        if self.min_success.value() > self.attempts.value():
            self.min_success.setValue(self.attempts.value())
        self.min_success.setMaximum(self.attempts.value())

    def split_priority_from_channels(self, text: str) -> tuple[str, str]:
        lines = CheckerWorker.normalize_channel_text(text)
        p1_set = {x.lower().replace("t.me/", "").replace("telegram.me/", "") for x in getattr(engine, "MAIN_CHANNELS", set())}
        p1: list[str] = []
        p2: list[str] = []
        seen: set[str] = set()
        for line in lines:
            ch = engine.normalize_channel(line)
            if not ch:
                continue
            key = ch.lower()
            if key in seen:
                continue
            seen.add(key)
            if key in p1_set:
                p1.append(f"t.me/{ch}")
            else:
                p2.append(f"t.me/{ch}")
        return "\n".join(p1), "\n".join(p2)

    def load_initial_values(self) -> None:
        engine.ensure_files()
        if engine.CHANNELS_FILE.exists():
            raw_channels = engine.CHANNELS_FILE.read_text(encoding="utf-8", errors="ignore")
        else:
            raw_channels = engine.DEFAULT_CHANNELS.strip()
        p1, p2 = self.split_priority_from_channels(raw_channels)
        self.priority1_editor.setPlainText(p1)
        self.priority2_editor.setPlainText(p2)
        self.per_channel.setValue(getattr(engine, "PER_CHANNEL_LIMIT", 20))
        self.main_limit.setValue(getattr(engine, "MAIN_CHANNEL_LIMIT", 30))
        self.fetch_workers.setValue(getattr(engine, "FETCH_WORKERS", 8))
        self.ping_workers.setValue(getattr(engine, "PING_WORKERS", 4))
        self.attempts.setValue(min(max(getattr(engine, "PING_ATTEMPTS", 2), 1), 8))
        self.min_success.setValue(min(max(getattr(engine, "MIN_SUCCESS", 1), 1), self.attempts.value()))
        idx = self.test_mode.findText(getattr(engine, "TEST_MODE", "auto"))
        self.test_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self.check_url.setText(getattr(engine, "CHECK_URL", "http://www.gstatic.com/generate_204"))
        self.tag_prefix.setText(getattr(engine, "SUB_TAG_PREFIX", "t.me/dicodeir"))
        self.rename_names.setChecked(bool(getattr(engine, "RENAME_CONFIG_NAMES", True)))
        self.check_configs.setChecked(bool(getattr(engine, "CHECK_V2RAY_CONFIGS", True)))
        self.check_proxies.setChecked(bool(getattr(engine, "CHECK_TELEGRAM_PROXIES", True)))
        self.fix_min_success()
        self.load_subscription_settings()
        self.update_channel_count()

    def load_subscription_settings(self) -> None:
        token = str(self.app_settings.value("subscription/github_token", ""))
        repo = str(self.app_settings.value("subscription/repository", ""))
        self.github_token.setText(token)
        self.subscription_repo.setText(repo)
        self._refresh_subscription_urls(repo)

    def _refresh_subscription_urls(self, repo: str) -> None:
        if "/" not in repo:
            self.subscription_sub_url.clear()
            self.subscription_proxy_url.clear()
            return
        owner, name = repo.split("/", 1)
        base = f"https://raw.githubusercontent.com/{owner}/{name}/refs/heads/main"
        self.subscription_sub_url.setText(f"{base}/sub.txt")
        self.subscription_proxy_url.setText(f"{base}/proxy.txt")

    def save_subscription_settings(self) -> None:
        token = self.github_token.text().strip()
        if not token:
            QMessageBox.warning(self, "توکن لازم است", "در GitHub از Settings > Developer settings > Personal access tokens > Tokens (classic)، یک توکن با scope «public_repo» بساز و اینجا وارد کن.")
            return
        self.app_settings.setValue("subscription/github_token", token)
        self.app_settings.setValue("subscription/repository", self.subscription_repo.text().strip())
        self.app_settings.sync()
        self.append_log("OK ساب اختصاصی فعال شد؛ بعد از پایان تست بعدی، فایل ها در GitHub منتشر می شوند.")
        QMessageBox.information(self, "ساب اختصاصی", "تنظیمات ذخیره شد. بعد از پایان تست، ریپازیتوری عمومی تصادفی با پایان DIC و لینک‌های raw برای sub.txt و proxy.txt ساخته می‌شوند.")

    def open_github_token_page(self) -> None:
        webbrowser.open(GITHUB_TOKEN_CREATE_URL)
        self.append_log("INFO صفحه ساخت GitHub token باز شد؛ پس از ساخت، توکن را در مرحله ۲ تنظیمات بچسبان.")

    def publish_personal_subscription(self) -> None:
        token = self.github_token.text().strip()
        if not token:
            return
        try:
            sub_text = engine.SUB_FILE.read_text(encoding="utf-8") if engine.SUB_FILE.exists() else ""
            proxy_text = engine.PROXY_FILE.read_text(encoding="utf-8") if engine.PROXY_FILE.exists() else ""
            repo = subscription_publisher.publish(token, self.subscription_repo.text().strip(), sub_text, proxy_text)
            self.subscription_repo.setText(repo.ref)
            self.app_settings.setValue("subscription/repository", repo.ref)
            self.app_settings.sync()
            self._refresh_subscription_urls(repo.ref)
            self.append_log(f"OK ساب اختصاصی به روز شد: {repo.ref}")
        except Exception as exc:
            self.append_log(f"WARN انتشار ساب اختصاصی ناموفق: {exc}")
            QMessageBox.warning(self, "ساب اختصاصی", f"خروجی محلی ساخته شد، اما انتشار GitHub ناموفق بود:\n{exc}")

    def load_default_channels(self) -> None:
        p1, p2 = self.split_priority_from_channels(engine.DEFAULT_CHANNELS.strip())
        self.priority1_editor.setPlainText(p1)
        self.priority2_editor.setPlainText(p2)
        self.update_channel_count()

    def priority_channel_lists(self) -> tuple[list[str], list[str]]:
        p1 = CheckerWorker.normalize_channel_text(self.priority1_editor.toPlainText())
        p2 = CheckerWorker.normalize_channel_text(self.priority2_editor.toPlainText())
        seen: set[str] = set()
        clean_p1: list[str] = []
        clean_p2: list[str] = []
        for group, target in ((p1, clean_p1), (p2, clean_p2)):
            for line in group:
                ch = engine.normalize_channel(line)
                if not ch:
                    continue
                key = ch.lower()
                if key in seen:
                    continue
                seen.add(key)
                target.append(f"t.me/{ch}")
        return clean_p1, clean_p2

    def save_channels_from_editor(self) -> None:
        p1, p2 = self.priority_channel_lists()
        combined = p1 + p2
        engine.CHANNELS_FILE.write_text("\n".join(combined) + "\n", encoding="utf-8")
        self.priority1_editor.setPlainText("\n".join(p1))
        self.priority2_editor.setPlainText("\n".join(p2))
        self.update_channel_count()
        self.append_log(f"OK لیست کانال‌ها ذخیره شد: رتبه اول {len(p1)} | رتبه دوم {len(p2)}")

    def dedupe_channels(self) -> None:
        p1, p2 = self.priority_channel_lists()
        self.priority1_editor.setPlainText("\n".join(p1))
        self.priority2_editor.setPlainText("\n".join(p2))
        self.update_channel_count()
        self.append_log(f"OK لیست پاکسازی شد: رتبه اول {len(p1)} | رتبه دوم {len(p2)}")

    def import_channels_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل کانال‌ها", str(engine.ROOT), "Text files (*.txt);;All files (*.*)")
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        current = self.priority2_editor.toPlainText().strip()
        merged = (current + "\n" + text).strip() if current else text
        self.priority2_editor.setPlainText(merged)
        self.dedupe_channels()

    def update_channel_count(self) -> None:
        if not hasattr(self, "channel_count"):
            return
        p1 = CheckerWorker.normalize_channel_text(self.priority1_editor.toPlainText()) if hasattr(self, "priority1_editor") else []
        p2 = CheckerWorker.normalize_channel_text(self.priority2_editor.toPlainText()) if hasattr(self, "priority2_editor") else []
        self.channel_count.setText(f"رتبه اول {len(p1)} | رتبه دوم {len(p2)}")

    def reset_settings(self) -> None:
        self.per_channel.setValue(20)
        self.main_limit.setValue(30)
        self.fetch_workers.setValue(10)
        self.ping_workers.setValue(4)
        self.prefilter_workers.setValue(64)
        self.attempts.setValue(2)
        self.min_success.setValue(1)
        idx = self.test_mode.findText("auto")
        self.test_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self.check_url.setText("http://www.gstatic.com/generate_204")
        self.tag_prefix.setText("t.me/dicodeir")
        self.rename_names.setChecked(True)
        self.rename_names.setLayoutDirection(Qt.RightToLeft)
        self.check_configs.setChecked(True)
        self.check_configs.setLayoutDirection(Qt.RightToLeft)
        self.check_proxies.setChecked(True)
        self.check_proxies.setLayoutDirection(Qt.RightToLeft)
        self.prefilter.setChecked(True)
        self.prefilter.setLayoutDirection(Qt.RightToLeft)
        self.append_log("INFO تنظیمات به حالت پیشنهادی برگشت.")

    def current_settings(self) -> RunSettings:
        return RunSettings(
            per_channel_limit=self.per_channel.value(),
            main_channel_limit=self.main_limit.value(),
            priority1_channels_text=self.priority1_editor.toPlainText(),
            priority2_channels_text=self.priority2_editor.toPlainText(),
            fetch_workers=self.fetch_workers.value(),
            fetch_timeout=15.0,
            test_mode=self.test_mode.currentText(),
            ping_attempts=self.attempts.value(),
            min_success=self.min_success.value(),
            ping_workers=self.ping_workers.value(),
            tcp_timeout=4.0,
            socket_timeout=8.0,
            xray_startup_wait=1.0,
            xray_process_timeout=14.0,
            check_url=self.check_url.text().strip() or "http://www.gstatic.com/generate_204",
            sub_tag_prefix=self.tag_prefix.text().strip() or "t.me/dicodeir",
            rename_config_names=self.rename_names.isChecked(),
            check_v2ray_configs=self.check_configs.isChecked(),
            check_telegram_proxies=self.check_proxies.isChecked(),
            prefilter_enabled=self.prefilter.isChecked(),
            prefilter_workers=self.prefilter_workers.value(),
        )

    def start_run(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if not self.check_configs.isChecked() and not self.check_proxies.isChecked():
            QMessageBox.warning(self, "خروجی انتخاب نشده", "حداقل یکی از خروجی‌ها را روشن کن: sub.txt یا proxy.txt")
            return
        priority_one, priority_two = self.priority_channel_lists()
        if not priority_one and not priority_two:
            QMessageBox.warning(self, "فهرست کانال خالی است", "هیچ کانال معتبری در تنظیمات نیست. ابتدا از بخش کانال‌ها «لیست پیش‌فرض» را بارگذاری و ذخیره کن.")
            return
        self.save_channels_from_editor()
        self.log_box.clear()
        self.clear_result_tabs()
        self.switch_page(0)
        self.set_running(True)
        self.btn_continue.setEnabled(False)
        self.step_collect.set_state("running", "در حال دریافت")
        self.step_test.set_state("blocked", "در انتظار")
        self.update_counters(0, 0, 0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_meta.setText("شروع شد")
        self.worker = CheckerWorker(self.current_settings())
        self.worker.log_line.connect(self.append_log)
        self.worker.stage_text.connect(self.set_stage)
        self.worker.progress.connect(self.update_progress)
        self.worker.counters.connect(self.update_counters)
        self.worker.ask_disconnect.connect(self.on_ask_disconnect)
        self.worker.paused.connect(self.on_paused)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def continue_run(self) -> None:
        if self.worker:
            self.btn_continue.setEnabled(False)
            self.step_test.set_state("running", "در حال تست")
            if getattr(self.worker, "_pause_requested", False):
                self.append_log("INFO ادامه تست از توقف موقت.")
                self.set_stage("ادامه تست")
                self.worker.resume_after_pause()
            else:
                self.append_log("INFO مرحله دوم تست شروع شد.")
                self.worker.continue_after_disconnect()

    def stop_run(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.btn_continue.setEnabled(True)
            self.step_test.set_state("ready", "آماده ادامه")
            self.progress_meta.setText("توقف موقت")
            self.append_log("INFO توقف موقت ثبت شد؛ برای ادامه روی دکمه ادامه بزن.")
            self.refresh_result_tabs()

    def reset_run(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_abort()
            try:
                engine.cleanup_xray_processes()
            except Exception:
                pass
            self.worker.wait(1500)
        self.set_running(False)
        self.btn_continue.setEnabled(False)
        self.btn_start.setText("شروع دریافت")
        self.btn_continue.setText("شروع تست واقعی")
        self.step_collect.set_state("idle", "آماده")
        self.step_test.set_state("blocked", "ابتدا مرحله ۱")
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_meta.setText("ریست شد")
        self.update_counters(0, 0, 0, 0)
        self.clear_result_tabs()
        self.append_log("INFO اجرا ریست شد؛ برای شروع دوباره روی شروع بررسی بزن.")

    def set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running and self.step_collect.property("state") == "idle")
        self.btn_stop.setEnabled(running)
        if hasattr(self, "btn_reset_run"):
            self.btn_reset_run.setEnabled(True)
        self.nav_settings.setEnabled(not running)
        self.nav_channels.setEnabled(not running)

    def on_ask_disconnect(self) -> None:
        self.step_collect.set_state("done", "تکمیل شد")
        self.btn_start.setEnabled(False)
        self.btn_start.setText("دریافت انجام شد")
        self.step_test.set_state("ready", "آماده تست")
        self.btn_continue.setText("شروع تست واقعی")
        self.btn_continue.setEnabled(True)
        self.progress_meta.setText("منتظر ادامه")
        QMessageBox.information(
            self,
            "مرحله دوم",
            "کانفیگ/فیلترشکن فعلی را کامل قطع کن. بعد داخل برنامه روی ادامه بزن تا تست واقعی از اینترنت خودت انجام شود.",
        )

    def on_paused(self) -> None:
        self.btn_continue.setEnabled(True)
        self.step_test.set_state("ready", "آماده ادامه")
        self.progress_meta.setText("توقف موقت")
        self.refresh_result_tabs()
        self.append_log("INFO خروجی‌های موقت ذخیره شدند؛ می‌توانی کپی کنی یا ادامه بدهی.")

    def on_finished(self, report: dict) -> None:
        self.set_running(False)
        self.btn_continue.setEnabled(False)
        self.set_stage("تمام شد")
        self.step_test.set_state("done", "تکمیل شد")
        self.btn_continue.setText("خروجی آماده است")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_meta.setText("خروجی ساخته شد")
        self.refresh_result_tabs()
        self.switch_page(getattr(self, "configs_page_index", 0))
        try:
            engine.cleanup_xray_processes()
        except Exception:
            pass
        self.publish_personal_subscription()
        stats = report.get("stats", {})
        QMessageBox.information(
            self,
            "خروجی ساخته شد",
            f"sub.txt: {stats.get('alive_configs', 0)} کانفیگ\nproxy.txt: {stats.get('alive_telegram_proxies', 0)} پروکسی\nردشده پروکسی: {stats.get('skipped_telegram_proxies', 0)}\nناموفق: {stats.get('dead_total', 0)}",
        )

    def on_failed(self, error: str) -> None:
        self.set_running(False)
        self.btn_continue.setEnabled(False)
        self.set_stage("خطا")
        self.step_test.set_state("blocked", "خطا")
        self.progress_meta.setText("خطا")
        self.append_log(f"ERROR: {error}")
        try:
            engine.cleanup_xray_processes()
        except Exception:
            pass
        QMessageBox.critical(self, "خطا", error)

    def set_stage(self, text: str) -> None:
        if hasattr(self, "stage_label"):
            self.stage_label.setText(text)
        self.progress_title.setText(text)

    def update_progress(self, done: int, total: int) -> None:
        total = max(total, 1)
        value = min(done, total)
        self.progress_bar.setRange(0, total)
        percent = int((value / total) * 100)
        self.progress_bar.setFormat(f"{percent}%  |  {done}/{total}")
        self.progress_meta.setText(f"{done}/{total}")
        if hasattr(self, "progress_anim"):
            self.progress_anim.stop()
            self.progress_anim.setStartValue(self.progress_bar.value())
            self.progress_anim.setEndValue(value)
            self.progress_anim.start()
        else:
            self.progress_bar.setValue(value)

    def update_counters(self, alive_configs: int, alive_proxies: int, dead: int, unsupported: int) -> None:
        self.card_alive_configs.set_value(alive_configs)
        self.card_alive_proxies.set_value(alive_proxies)
        self.card_dead.set_value(dead)
        self.card_unsupported.set_value(unsupported)

    def append_log(self, line: str) -> None:
        if not hasattr(self, "log_box"):
            return
        safe = html_lib.escape(line)
        color = "#a7b4c7"
        bg = "transparent"
        border = "#1f2937"
        tag = "LOG"
        if "ERROR" in line or "FAIL" in line or "خطا" in line:
            color = "#ff7b8a"; bg = "#1a0b10"; border = "#4b1d28"; tag = "ERR"
        elif "OK" in line or "تمام شد" in line or "آماده" in line:
            color = "#63e6be"; bg = "#071510"; border = "#164d3c"; tag = "OK"
        elif "INFO" in line or "مرحله" in line or "شروع" in line:
            color = "#7dd3fc"; bg = "#07131f"; border = "#1d4b68"; tag = "INF"
        elif "Prefilter" in line or "Xray" in line:
            color = "#fde68a"; bg = "#171204"; border = "#55441b"; tag = "RUN"
        self.log_box.append(
            f'<div style="direction:rtl; unicode-bidi:plaintext; color:{color}; background:{bg}; border:1px solid {border}; padding:7px 10px; border-radius:10px; margin:3px 0;">'
            f'<span style="color:#e5edf7; font-weight:800;">{tag}</span>&nbsp;&nbsp;{safe}</div>'
        )
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def refresh_result_tabs(self) -> None:
        if not hasattr(self, "config_results"):
            return
        sub_text = ""
        proxy_text = ""
        try:
            if engine.SUB_FILE.exists():
                sub_text = engine.SUB_FILE.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            sub_text = ""
        try:
            if engine.PROXY_FILE.exists():
                proxy_text = engine.PROXY_FILE.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            proxy_text = ""
        sub_count = len([x for x in sub_text.splitlines() if x.strip()])
        proxy_count = len([x for x in proxy_text.splitlines() if x.strip()])
        self.config_results.setPlainText(sub_text.strip() or "هنوز خروجی sub.txt ساخته نشده است.")
        self.proxy_results.setPlainText(proxy_text.strip() or "هنوز خروجی proxy.txt ساخته نشده است.")
        if hasattr(self, "config_count_label"):
            self.config_count_label.setText(f"{sub_count} کانفیگ")
        if hasattr(self, "proxy_count_label"):
            self.proxy_count_label.setText(f"{proxy_count} پروکسی")

    def copy_result_box(self, kind: str) -> None:
        box = self.proxy_results if kind == "proxies" else self.config_results
        name = "proxy.txt" if kind == "proxies" else "sub.txt"
        text = box.toPlainText().strip()
        if not text or text.startswith("هنوز خروجی") or text.startswith("در حال"):
            self.append_log(f"INFO چیزی برای کپی کردن در {name} نیست.")
            return
        QApplication.clipboard().setText(text)
        self.append_log(f"OK محتوای {name} کپی شد.")

    def copy_current_result_tab(self) -> None:
        current = self.pages.currentIndex()
        if current == getattr(self, "proxies_page_index", -1):
            self.copy_result_box("proxies")
        else:
            self.copy_result_box("configs")

    def clear_result_tabs(self) -> None:
        if hasattr(self, "config_results"):
            self.config_results.setPlainText("در حال آماده‌سازی خروجی...")
            self.proxy_results.setPlainText("در حال آماده‌سازی خروجی...")
            self.config_count_label.setText("0 کانفیگ")
            self.proxy_count_label.setText("0 پروکسی")

    def open_output_folder(self) -> None:
        path = str(engine.ROOT)
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{path}")

    def animate_sidebar_width(self, target: int) -> None:
        if not hasattr(self, "sidebar"):
            return
        start = self.sidebar.width() or target
        if abs(start - target) < 2:
            self.sidebar.setFixedWidth(target)
            return
        self.sidebar.setMinimumWidth(min(start, target))
        self.sidebar.setMaximumWidth(max(start, target))
        anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        anim.setDuration(130)
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: self.sidebar.setFixedWidth(target))
        self._sidebar_anim = anim
        anim.start()

    def toggle_sidebar(self) -> None:
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.apply_responsive_mode(force=True)

    def update_window_rounding(self) -> None:
        maximized = self.isMaximized()
        if hasattr(self, "root_layout"):
            self.root_layout.setContentsMargins(0 if maximized else 10, 0 if maximized else 10, 0 if maximized else 10, 0 if maximized else 10)
        if hasattr(self, "root"):
            self.root.setProperty("maximized", maximized)
            self.root.style().unpolish(self.root)
            self.root.style().polish(self.root)
            self.root.update()

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.btn_maximize.setText("□")
        else:
            self.showMaximized()
            self.btn_maximize.setText("❐")
        QTimer.singleShot(20, self.update_window_rounding)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and event.position().y() <= 76:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_position is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            if self.worker and self.worker.isRunning():
                self.worker.request_abort()
            engine.cleanup_xray_processes()
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.apply_responsive_mode()
        self.update_window_rounding()

    def apply_responsive_mode(self, force: bool = False) -> None:
        width = self.width()
        compact = self.sidebar_collapsed or width < 1050
        if force or compact != self.compact_nav:
            self.compact_nav = compact
            self.animate_sidebar_width(76 if compact else 216)
            self.sidebar_caption.setVisible(not compact)
            self.btn_open_side.setText("" if compact else "پوشه خروجی")
            self.btn_open_side.setToolTip("پوشه خروجی")
            for btn, text in (
                (self.nav_dashboard, "داشبورد"),
                (self.nav_settings, "تنظیمات"),
                (self.nav_channels, "کانال‌ها"),
                (self.nav_configs, "کانفیگ‌ها"),
                (self.nav_proxies, "پروکسی‌ها"),
            ):
                btn.setText("" if compact else text)
                btn.setToolTip(text)
                btn.setToolButtonStyle(Qt.ToolButtonIconOnly if compact else Qt.ToolButtonTextBesideIcon)
                btn.setMinimumWidth(46 if compact else 170)
        self.subtitle_label.setVisible(width >= 880)
        columns = 1 if width < 900 else 2 if width < 1240 else 4
        for i, card in enumerate(self.stat_cards):
            self.cards_grid.removeWidget(card)
            self.cards_grid.addWidget(card, i // columns, i % columns)

    def apply_style(self) -> None:
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.setFont(QFont("Vazirmatn", 10))
        self.setLayoutDirection(Qt.LeftToRight)
        self.setStyleSheet("""
            * { outline: none; }
            QMainWindow { background: transparent; }
            QWidget {
                background: transparent;
                color: #e5edf7;
                font-family: Vazirmatn, Vazir, Segoe UI, Arial;
                font-size: 13px;
            }
            QLabel { background: transparent; }
            #AppRoot {
                background: #11141a;
                border: 1px solid #252b35;
                border-radius: 22px;
            }
            #AppRoot[maximized="true"] {
                border-radius: 0px;
                border: none;
            }
            #TopBar {
                background: #12161d;
                border: 1px solid #242d3a;
                border-radius: 20px;
            }
            #Sidebar, #ContentPanel {
                background: #11151c;
                border: 1px solid #202938;
                border-radius: 22px;
            }
            #Panel, #PageHeader, #StatCard {
                background: #12161d;
                border: 1px solid #222c3a;
                border-radius: 18px;
            }
            #Panel:hover, #PageHeader:hover, #StatCard:hover {
                background: #111821;
                border-color: #2f3b4d;
            }
            QStackedWidget, QStackedWidget > QWidget, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            #Title {
                font-size: 22px;
                font-weight: 900;
                color: #ffffff;
                letter-spacing: -0.25px;
            }
            #PageTitle {
                font-size: 18px;
                font-weight: 900;
                color: #ffffff;
            }
            #Subtitle, #Muted, #CardLabel, #FieldLabel, #SidebarCaption {
                color: #9aa8ba;
                font-size: 12px;
            }
            #SidebarCaption {
                font-weight: 800;
                padding: 4px 8px 8px 8px;
            }
            #SectionTitle {
                color: #f6f8fb;
                font-size: 15px;
                font-weight: 900;
            }
            #PageTitle, #Subtitle, #FieldLabel, #SectionTitle, #Hint, #SidebarCaption {
                qproperty-alignment: AlignRight;
            }
            #Title { qproperty-alignment: AlignLeft; }
            #Hint { text-align: right; direction: rtl; }
            #StagePill, #VersionPill, #SoftPill {
                background: #101926;
                color: #c9d7e8;
                border: 1px solid #29364a;
                border-radius: 14px;
                padding: 8px 12px;
                font-weight: 900;
            }
            #StagePill {
                color: #67e8f9;
                border-color: #25506d;
            }
            #CardIcon, #LargeIcon {
                background: #111d2b;
                border: 1px solid #2a455f;
                border-radius: 13px;
            }
            #CardValue {
                color: #67e8f9;
                font-size: 26px;
                font-weight: 900;
            }
            #SettingsSection {
                background: #0f141c;
                border: 1px solid #202a39;
                border-radius: 18px;
            }
            #FieldBox, #OptionsBox, #ResetBox {
                background: #0f131a;
                border: 1px solid #202a39;
                border-radius: 15px;
            }
            QFrame#FieldBox[accent="0"] { border-color: #23364f; background: #0d131c; }
            QFrame#FieldBox[accent="1"] { border-color: #243b36; background: #0b1614; }
            QFrame#FieldBox[accent="2"] { border-color: #3c334d; background: #120f1b; }
            QFrame#FieldBox[accent="3"] { border-color: #4a3720; background: #171107; }
            QFrame#FieldBox[accent="4"] { border-color: #3f2832; background: #160d12; }
            QToolButton {
                background: transparent;
                color: #c5d0de;
                border: 1px solid transparent;
                border-radius: 13px;
                padding: 9px 10px;
                font-weight: 900;
                text-align: left;
            }
            QToolButton:hover {
                background: #151d27;
                border-color: #303b4f;
                color: #ffffff;
            }
            QToolButton:checked {
                background: #172335;
                border-color: #3b82f6;
                color: #ffffff;
            }
            QToolButton#TopIconButton, QToolButton#WindowButton {
                background: #111821;
                color: #dbe7f5;
                border: 1px solid #273246;
                border-radius: 13px;
                font-weight: 900;
            }
            QToolButton#TopIconButton:hover, QToolButton#WindowButton:hover {
                background: #182232;
                border-color: #3b82f6;
            }
            QToolButton#CloseButton {
                background: #1a0b10;
                color: #ff9ca8;
                border: 1px solid #49202b;
                border-radius: 13px;
                font-weight: 900;
            }
            QToolButton#CloseButton:hover {
                background: #ef4444;
                color: white;
                border-color: #ff7a86;
            }
            #HomeStepCard {
                background: #0f151e;
                border: 1px solid #263244;
                border-radius: 18px;
            }
            #HomeStepCard[state="ready"] { border-color: #2563eb; background: #0d1725; }
            #HomeStepCard[state="running"] { border-color: #38bdf8; background: #0b1a29; }
            #HomeStepCard[state="done"] { border-color: #216c57; background: #0a1714; }
            #HomeStepCard[state="blocked"] { border-color: #202a39; background: #0c1118; }
            #StepNumber {
                background: #142238;
                color: #67e8f9;
                border: 1px solid #29496b;
                border-radius: 16px;
                font-size: 14px;
                font-weight: 900;
            }
            #StepTitle { color: #f5f9ff; font-size: 15px; font-weight: 900; }
            #StepState {
                background: #172235;
                color: #93c5fd;
                border-radius: 9px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 900;
            }
            #HomeStepCard[state="done"] #StepState { background: #102a23; color: #63e6be; }
            #HomeStepCard[state="blocked"] #StepState { background: #151b24; color: #718096; }
            QPushButton {
                background: #111821;
                border: 1px solid #263244;
                border-radius: 14px;
                padding: 10px 14px;
                color: #edf3fb;
                font-weight: 900;
            }
            QPushButton:hover {
                background: #172233;
                border-color: #3b82f6;
            }
            QPushButton:pressed {
                background: #0c121a;
                padding-top: 11px;
                padding-bottom: 9px;
            }
            QPushButton:disabled {
                color: #617086;
                border-color: #1b2430;
                background: #0c1118;
            }
            QPushButton#PrimaryButton {
                background: #2563eb;
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
            QPushButton#PrimaryButton:hover {
                background: #1d4ed8;
                border-color: #67e8f9;
            }
            QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
                background: #0f131a;
                border: 1px solid #263244;
                border-radius: 12px;
                padding: 9px;
                color: #edf3fb;
                selection-background-color: #2563eb;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
                border-color: #3b82f6;
                background: #0e1620;
            }
            QSpinBox { padding-right: 9px; padding-left: 9px; }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px; height: 0px; border: none; background: transparent;
            }
            QComboBox::drop-down { width: 26px; border: none; background: transparent; }
            QComboBox::down-arrow { image: none; border: none; width: 0; height: 0; }
            QComboBox QAbstractItemView {
                background: #0f131a;
                border: 1px solid #263244;
                color: #edf3fb;
                selection-background-color: #172335;
                outline: none;
            }
            QTextEdit#LogBox, QPlainTextEdit {
                font-family: Consolas, Vazirmatn, monospace;
                font-size: 12px;
                line-height: 150%;
            }

            QTextEdit#ResultBox {
                font-family: Consolas, Vazirmatn, monospace;
                font-size: 12px;
                border-color: #2f3c50;
                background: #0b1016;
            }
            QProgressBar {
                background: #0f131a;
                border: 1px solid #263244;
                border-radius: 12px;
                min-height: 28px;
                text-align: center;
                font-weight: 900;
                color: #ffffff;
            }
            QProgressBar::chunk {
                border-radius: 11px;
                background: #3b82f6;
            }
            QCheckBox {
                color: #e5edf7;
                font-weight: 900;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border-radius: 5px;
                border: 1px solid #3a4658;
                background: #0f131a;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border: 1px solid #7dd3fc;
            }
            #Hint {
                background: #12161d;
                border: 1px solid #222c3a;
                border-radius: 15px;
                color: #a7b4c7;
                padding: 14px;
            }
            QScrollBar:vertical {
                background: #0f131a;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #29364a;
                border-radius: 5px;
                min-height: 34px;
            }
            QScrollBar::handle:vertical:hover { background: #3b4a60; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0; background: transparent;
            }
            QTabWidget#ResultsTabs::pane {
                border: 1px solid #263244;
                border-radius: 14px;
                background: #0f131a;
                top: -1px;
            }
            QTabWidget#ResultsTabs::tab-bar {
                alignment: right;
            }
            QTabBar::tab {
                background: #101720;
                color: #9aa8ba;
                border: 1px solid #263244;
                border-bottom: none;
                padding: 9px 18px;
                margin-left: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 900;
            }
            QTabBar::tab:selected {
                background: #182132;
                color: #ffffff;
                border-color: #3b82f6;
            }
            QTextEdit#ResultBox {
                font-family: Consolas, Vazirmatn, monospace;
                font-size: 12px;
                background: #0b0f14;
                border: none;
                border-radius: 12px;
                color: #dbe7f5;
                padding: 10px;
            }
            QMessageBox {
                background: #0f1218;
                color: #edf3fb;
                font-family: Vazirmatn, Vazir, Segoe UI, Arial;
            }
            QMessageBox QLabel {
                color: #edf3fb;
                font-family: Vazirmatn, Vazir, Segoe UI, Arial;
                qproperty-alignment: AlignRight;
            }
        """)


def set_windows_app_id() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dicode.ConfigChecker.1")
    except Exception:
        pass


def main() -> int:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    icon_path = resource_path("assets", "app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
